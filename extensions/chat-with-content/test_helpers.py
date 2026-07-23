# Unit tests for the pure helpers. The Shiny app (app.py) is intentionally kept
# thin over these functions so the logic can be tested without a running session
# or any LLM / Connect calls.
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import helpers


def iso_ago(**delta):
    # ISO timestamp `delta` in the past, in the "...Z" form Connect returns.
    dt = datetime.now(timezone.utc) - timedelta(**delta)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_item(**overrides):
    item = {
        "guid": "g1",
        "name": "the-name",
        "title": "The Title",
        "app_mode": "static",
        "app_role": "owner",
        "content_category": "",
        "last_deployed_time": iso_ago(hours=2),
        "owner": SimpleNamespace(first_name="Ada", last_name="Lovelace"),
    }
    item.update(overrides)
    return SimpleNamespace(**item)


# --- running_on_connect ----------------------------------------------------


def test_running_on_connect_detects_either_env_var(monkeypatch):
    monkeypatch.delenv("RSTUDIO_PRODUCT", raising=False)
    monkeypatch.setenv("POSIT_PRODUCT", "CONNECT")
    assert helpers.running_on_connect() is True

    monkeypatch.delenv("POSIT_PRODUCT", raising=False)
    monkeypatch.setenv("RSTUDIO_PRODUCT", "CONNECT")
    assert helpers.running_on_connect() is True


def test_running_on_connect_false_off_connect(monkeypatch):
    monkeypatch.delenv("POSIT_PRODUCT", raising=False)
    monkeypatch.delenv("RSTUDIO_PRODUCT", raising=False)
    assert helpers.running_on_connect() is False


# --- resolve_visitor_client ------------------------------------------------


class _FakeError(Exception):
    def __init__(self, error_code=None, error_message=None):
        self.error_code = error_code
        self.error_message = error_message


class _FakeClient:
    def __init__(self, raises=None, scoped="scoped-client"):
        self._raises = raises
        self._scoped = scoped

    def with_user_session_token(self, token):
        if self._raises:
            raise self._raises
        return self._scoped


def test_resolve_visitor_off_connect_uses_client_as_is():
    c = _FakeClient()
    assert helpers.resolve_visitor_client(c, False, None) == (c, True, None)


def test_resolve_visitor_no_token_on_connect_requires_setup():
    # The key fix: no session token on Connect must NOT fall back to the deploy
    # client (which would list the deployer's content); it requires setup.
    c = _FakeClient()
    assert helpers.resolve_visitor_client(c, True, None) == (c, False, None)


def test_resolve_visitor_scopes_to_the_viewer_with_a_token():
    c = _FakeClient(scoped="viewer-client")
    assert helpers.resolve_visitor_client(c, True, "tok") == (
        "viewer-client",
        True,
        None,
    )


def test_resolve_visitor_missing_integration_requires_setup():
    c = _FakeClient(raises=_FakeError(error_code=212))
    assert helpers.resolve_visitor_client(c, True, "tok") == (c, False, None)


def test_resolve_visitor_other_error_is_surfaced():
    c = _FakeClient(raises=_FakeError(error_code=5, error_message="permission denied"))
    assert helpers.resolve_visitor_client(c, True, "tok") == (
        c,
        True,
        "permission denied",
    )


# --- time_since_deployment -------------------------------------------------


def test_time_since_deployment_none_and_empty():
    assert helpers.time_since_deployment(None) == ""
    assert helpers.time_since_deployment("") == ""


def test_time_since_deployment_malformed_returns_empty():
    # A malformed timestamp must not raise (it would otherwise crash the whole
    # content list); it just omits the "last deployed" phrase.
    assert helpers.time_since_deployment("not-a-date") == ""


def test_time_since_deployment_future():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert helpers.time_since_deployment(future) == "last deployed in the future"


def test_time_since_deployment_units_and_pluralization():
    assert helpers.time_since_deployment(iso_ago(seconds=5)) == "last deployed 5 seconds ago"
    assert helpers.time_since_deployment(iso_ago(seconds=90)) == "last deployed 1 minute ago"
    assert helpers.time_since_deployment(iso_ago(minutes=5)) == "last deployed 5 minutes ago"
    assert helpers.time_since_deployment(iso_ago(hours=2)) == "last deployed 2 hours ago"
    assert helpers.time_since_deployment(iso_ago(days=1, hours=1)) == "last deployed 1 day ago"
    assert helpers.time_since_deployment(iso_ago(days=20)) == "last deployed 2 weeks ago"
    assert helpers.time_since_deployment(iso_ago(days=45)) == "last deployed 1 month ago"
    assert helpers.time_since_deployment(iso_ago(days=400)) == "last deployed 1 year ago"


# --- is_chattable_content --------------------------------------------------


def test_is_chattable_content_accepts_static_content():
    assert helpers.is_chattable_content(make_item()) is True
    assert helpers.is_chattable_content(make_item(app_mode="quarto-static")) is True


def test_is_chattable_content_rejects_interactive_apps():
    assert helpers.is_chattable_content(make_item(app_mode="python-shiny")) is False


def test_is_chattable_content_rejects_unpublished_and_pins():
    assert helpers.is_chattable_content(make_item(app_role="none")) is False
    assert helpers.is_chattable_content(make_item(content_category="pin")) is False


# --- content_choice_label --------------------------------------------------


def test_content_choice_label_full():
    label = helpers.content_choice_label(make_item())
    assert label == "The Title - Ada Lovelace last deployed 2 hours ago"


def test_content_choice_label_falls_back_to_name_then_guid():
    assert helpers.content_choice_label(make_item(title=None)).startswith("the-name")
    assert helpers.content_choice_label(
        make_item(title=None, name=None)
    ).startswith("g1")


def test_content_choice_label_tolerates_missing_owner_and_date():
    label = helpers.content_choice_label(
        make_item(owner=None, last_deployed_time=None)
    )
    # No owner and no deploy time -> just the title, no dangling " - ".
    assert label == "The Title"


def test_content_choice_label_handles_blank_owner_names():
    label = helpers.content_choice_label(
        make_item(
            owner=SimpleNamespace(first_name=None, last_name=None),
            last_deployed_time=None,
        )
    )
    assert label == "The Title"


# --- truncate_for_context --------------------------------------------------


def test_truncate_for_context_leaves_short_content_untouched():
    text = "a" * 100
    assert helpers.truncate_for_context(text, max_chars=1000) == text


def test_truncate_for_context_caps_long_content():
    text = "a" * 5000
    result = helpers.truncate_for_context(text, max_chars=1000)
    assert result.startswith("a" * 1000)
    assert "truncated" in result
    assert len(result) < len(text)


# --- content_ready ---------------------------------------------------------


def test_content_ready_true_when_session_llm_and_integration_all_present():
    assert helpers.content_ready(None, object(), True) is True


def test_content_ready_false_on_token_error():
    # A token error leaves the client as the unscoped deploy client, so content
    # must not load even though the integration flag is True.
    assert helpers.content_ready("exchange failed", object(), True) is False


def test_content_ready_false_without_llm():
    assert helpers.content_ready(None, None, True) is False


def test_content_ready_false_when_integration_disabled():
    assert helpers.content_ready(None, object(), False) is False
