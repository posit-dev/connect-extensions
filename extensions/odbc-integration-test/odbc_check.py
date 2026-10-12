"""Checks for an ODBC integration on Posit Connect.

Each check returns a Result. The checks never raise, so the report renders
even when the content runtime has no ODBC driver manager.
"""

import os
import shutil
import subprocess

ENV_VAR = "CONNECT_ODBC_CONNECTION_STRING"

PASS = "pass"
FAIL = "fail"
SKIP = "skip"

# Keys whose values the report never shows.
SECRET_KEYS = {"pwd", "password"}


class Result:
    def __init__(self, title, status, message, details=None, output=None):
        self.title = title
        self.status = status
        self.message = message
        self.details = details or []
        # Raw text from a driver or a tool, shown in a code block.
        self.output = output


def parse_pairs(text):
    """Parse "key=value;" pairs. A value that starts with "{" runs to the
    matching "}", and "}}" inside it is a literal "}". Raises ValueError
    with a message that names keys only, never values."""
    pairs = []
    i = 0
    while i < len(text):
        if text[i:].strip() == "":
            break
        eq = text.find("=", i)
        if eq < 0:
            raise ValueError("pair %d has no '='" % (len(pairs) + 1))
        key = text[i:eq].strip()
        if not key:
            raise ValueError("pair %d has an empty key" % (len(pairs) + 1))
        i = eq + 1
        if i < len(text) and text[i] == "{":
            i += 1
            value = []
            closed = False
            while i < len(text):
                if text[i] == "}":
                    if text[i + 1 : i + 2] == "}":
                        value.append("}")
                        i += 2
                        continue
                    i += 1
                    closed = True
                    break
                value.append(text[i])
                i += 1
            if not closed:
                raise ValueError("the value for key %s has no closing brace" % key)
            value = "".join(value)
            while i < len(text) and text[i] == " ":
                i += 1
        else:
            end = text.find(";", i)
            if end < 0:
                end = len(text)
            value = text[i:end]
            i = end
        pairs.append((key, value))
        if i < len(text) and text[i] == ";":
            i += 1
    return pairs


def find_key(pairs, name):
    for key, value in pairs:
        if key.lower() == name.lower():
            return value
    return None


def redact(text, pairs):
    """Replace each secret value in text with "****"."""
    for key, value in pairs:
        if key.lower() in SECRET_KEYS and value:
            text = text.replace(value, "****")
    return text


def check_variable(environ=None):
    environ = os.environ if environ is None else environ
    title = "Integration variable"
    value = environ.get(ENV_VAR, "")
    if not value:
        return Result(
            title,
            FAIL,
            "`%s` is not set. Add an ODBC integration to this content in the "
            "**Access** panel, then render the report again." % ENV_VAR,
        ), None
    try:
        pairs = parse_pairs(value)
    except ValueError as e:
        return Result(title, FAIL, "Connect set `%s`, but it does not parse: %s." % (ENV_VAR, e)), None
    keys = ", ".join("`%s`" % key for key, _ in pairs)
    return Result(title, PASS, "Connect set `%s` with these keys: %s." % (ENV_VAR, keys)), pairs


def check_driver_manager(import_pyodbc=None):
    title = "ODBC driver manager"
    try:
        if import_pyodbc is None:
            import pyodbc
        else:
            pyodbc = import_pyodbc()
    except ImportError as e:
        return Result(
            title,
            FAIL,
            "Python cannot load `pyodbc`. This usually means that unixODBC is "
            "not installed in the content runtime. Install the Posit "
            "Professional Drivers, which also install unixODBC.",
            output=str(e),
        ), None
    output = None
    odbcinst = shutil.which("odbcinst")
    if odbcinst:
        try:
            output = subprocess.run([odbcinst, "-j"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return Result(title, PASS, "unixODBC is installed.", output=output or None), pyodbc


def check_driver(pyodbc, pairs):
    title = "Driver registration"
    if pyodbc is None or pairs is None:
        return Result(title, SKIP, "Skipped, because an earlier check failed.")
    driver = find_key(pairs, "DRIVER")
    if driver is not None:
        installed = pyodbc.drivers()
        listed = ["`%s`" % name for name in installed] or ["none"]
        if any(name.lower() == driver.lower() for name in installed):
            return Result(title, PASS, "The driver `%s` is registered in `odbcinst.ini`." % driver)
        return Result(
            title,
            FAIL,
            "The driver `%s` is not registered in `odbcinst.ini`. Copy the "
            "Posit Professional Drivers sample to `odbcinst.ini`, or set "
            "**Driver name** in the integration to one of the registered "
            "drivers." % driver,
            ["Registered drivers: %s" % ", ".join(listed)],
        )
    dsn = find_key(pairs, "DSN")
    if dsn is not None:
        sources = pyodbc.dataSources()
        if any(name.lower() == dsn.lower() for name in sources):
            return Result(title, PASS, "The DSN `%s` is defined in `odbc.ini`." % dsn)
        return Result(title, FAIL, "The DSN `%s` is not defined in `odbc.ini`." % dsn)
    return Result(title, FAIL, "The connection string has no `DRIVER` or `DSN` key.")


# Hints for SQLSTATE values that the Posit Professional Drivers return.
HINTS = {
    "IM002": "The driver manager did not find the driver or DSN. Compare the name with `odbcinst.ini` or `odbc.ini`.",
    "IM003": "The driver manager found the driver, but it cannot load the driver library.",
    "08001": "The driver cannot reach the database. Check the host, the port, the network path from the content runtime, and any TLS settings in **Additional options**.",
    "08S01": "The network connection to the database failed. Check the host, the port, and any TLS settings in **Additional options**.",
    "HYT00": "The connection timed out. Check the host, the port, and the network path from the content runtime.",
    "28000": "The database rejected the username or the password.",
    "28P01": "The database rejected the username or the password.",
}

LIBRARY_HINT = (
    "The driver library or one of its dependencies is missing. Run `ldd` on "
    "the driver library from `odbcinst.ini` to find the missing library. The "
    "PostgreSQL driver needs Kerberos libraries, and the Oracle driver needs "
    "Oracle Instant Client."
)


def hint_for(sqlstate, message):
    if "can't open lib" in message.lower():
        return LIBRARY_HINT
    return HINTS.get(sqlstate)


def check_connection(pyodbc, pairs, connection_string, timeout=15):
    title = "Database connection"
    if pyodbc is None or pairs is None:
        return Result(title, SKIP, "Skipped, because an earlier check failed.")
    try:
        con = pyodbc.connect(connection_string, timeout=timeout, autocommit=True)
    except pyodbc.Error as e:
        sqlstate = str(e.args[0]) if e.args else ""
        message = redact(str(e.args[1]) if len(e.args) > 1 else str(e), pairs)
        hint = hint_for(sqlstate, message)
        return Result(title, FAIL, hint or "The connection failed.", ["SQLSTATE `%s`" % sqlstate], output=message)
    try:
        name = con.getinfo(pyodbc.SQL_DBMS_NAME)
        version = con.getinfo(pyodbc.SQL_DBMS_VER)
    finally:
        con.close()
    return Result(title, PASS, "Connected to %s %s." % (name, version))


def run_checks(environ=None):
    environ = os.environ if environ is None else environ
    variable, pairs = check_variable(environ)
    manager, pyodbc = check_driver_manager()
    driver = check_driver(pyodbc, pairs)
    if driver.status == FAIL:
        connection = Result("Database connection", SKIP, "Skipped, because an earlier check failed.")
    else:
        connection = check_connection(pyodbc, pairs, environ.get(ENV_VAR, ""))
    return [variable, manager, driver, connection]
