import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import odbc_check as oc


def test_parse_plain_and_braced():
    pairs = oc.parse_pairs("DRIVER={PostgreSQL};Server=db;PWD={a}}b;c};")
    assert pairs == [("DRIVER", "PostgreSQL"), ("Server", "db"), ("PWD", "a}b;c")]


def test_parse_no_final_semicolon():
    assert oc.parse_pairs("DSN=test") == [("DSN", "test")]


def test_parse_unclosed_brace_names_key_only():
    with pytest.raises(ValueError, match="PWD"):
        oc.parse_pairs("PWD={secret")


def test_variable_missing():
    result, pairs = oc.check_variable({})
    assert result.status == oc.FAIL and pairs is None


def test_variable_lists_keys_not_values():
    result, _ = oc.check_variable({oc.ENV_VAR: "DRIVER={X};UID=u;PWD=topsecret;"})
    assert result.status == oc.PASS
    assert "topsecret" not in result.message and "`PWD`" in result.message


def test_redact():
    pairs = [("UID", "u"), ("Password", "hunter2")]
    assert oc.redact("login hunter2 failed", pairs) == "login **** failed"


def test_driver_manager_missing():
    def boom():
        raise ImportError("libodbc.so.2: cannot open shared object file")

    result, mod = oc.check_driver_manager(boom)
    assert result.status == oc.FAIL and mod is None


class FakePyodbc:
    def drivers(self):
        return ["PostgreSQL", "SQLServer"]

    def dataSources(self):
        return {"test": "PostgreSQL"}


def test_driver_registered_ignores_case():
    result = oc.check_driver(FakePyodbc(), [("DRIVER", "postgresql")])
    assert result.status == oc.PASS


def test_driver_missing_lists_registered():
    result = oc.check_driver(FakePyodbc(), [("DRIVER", "Oracle")])
    assert result.status == oc.FAIL
    assert "`SQLServer`" in result.details[0]


def test_dsn():
    assert oc.check_driver(FakePyodbc(), [("DSN", "test")]).status == oc.PASS
    assert oc.check_driver(FakePyodbc(), [("DSN", "nope")]).status == oc.FAIL


def test_hints():
    assert oc.hint_for("01000", "[unixODBC][Driver Manager]Can't open lib 'x'") == oc.LIBRARY_HINT
    assert "password" in oc.hint_for("28P01", "")
    assert oc.hint_for("99999", "other") is None
