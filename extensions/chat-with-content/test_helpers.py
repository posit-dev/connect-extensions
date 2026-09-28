# Unit tests for the pure helpers. Logic goes in helpers.py when it can be tested
# without a running Shiny session or any LLM / Connect calls; what stays in app.py
# needs a live session, so it is checked by running the app.
from datetime import datetime, timedelta, timezone

import pytest
from posit.connect.content import ContentItem

import helpers

# "now" is frozen for the time tests so a bucket boundary can be asserted exactly
# and a slow test run can't tip "5 seconds" over to "6 seconds".
FROZEN_NOW = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_now(monkeypatch):
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FROZEN_NOW

    monkeypatch.setattr(helpers, "datetime", _FrozenDatetime)


def ago(**delta):
    # ISO timestamp `delta` before FROZEN_NOW, in the "...Z" form Connect returns.
    return (FROZEN_NOW - timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


class _FakeContext(dict):
    # ContentItem wants a context to make further requests with. The helpers never
    # trigger one, so an empty stand-in is enough.
    pass


def make_item(**overrides):
    # A real ContentItem, not a look-alike. The SDK raises on an absent field and
    # exposes `owner` as a property that fetches over HTTP, so a hand-rolled fake
    # can pass while the real object fails.
    fields = {
        "guid": "g1",
        "name": "the-name",
        "title": "The Title",
        "app_mode": "static",
        "app_role": "owner",
        "content_category": "",
        "last_deployed_time": ago(hours=2),
        "owner": {"first_name": "Ada", "last_name": "Lovelace"},
    }
    fields.update(overrides)
    # None means "Connect left this field out", so drop the key entirely rather
    # than sending a None the real payload would never contain.
    return ContentItem(
        _FakeContext(), **{k: v for k, v in fields.items() if v is not None}
    )


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


def test_running_on_connect_false_on_another_posit_product(monkeypatch):
    monkeypatch.delenv("RSTUDIO_PRODUCT", raising=False)
    monkeypatch.setenv("POSIT_PRODUCT", "WORKBENCH")
    assert helpers.running_on_connect() is False


# --- resolve_visitor_client ------------------------------------------------


class _FakeError(Exception):
    def __init__(self, error_code=None, error_message=None):
        self.error_code = error_code
        self.error_message = error_message


class _FakeSession:
    # Records what with_request_timeout mounts, so a test can assert the deadline
    # was applied without making a real request.
    def __init__(self):
        self.adapters = {}

    def mount(self, prefix, adapter):
        self.adapters[prefix] = adapter


class _FakeClient:
    def __init__(self, raises=None, scoped=None):
        self._raises = raises
        self._scoped = scoped
        self.session = _FakeSession()

    def with_user_session_token(self, token):
        if self._raises:
            raise self._raises
        return self._scoped


def test_resolve_visitor_off_connect_uses_client_as_is():
    c = _FakeClient()
    assert helpers.resolve_visitor_client(c, False, None) == (c, True, None)


def test_resolve_visitor_no_token_on_connect_never_uses_the_deploy_client():
    # No session token on Connect must NOT fall back to the deploy client, which
    # would list the deployer's content as if it were the viewer's.
    client, integration_enabled, detail = helpers.resolve_visitor_client(
        _FakeClient(), True, None
    )
    assert detail is not None
    # It must NOT be reported as a missing integration: neither being signed out nor
    # server-wide OAuth being off is fixed by adding one, so the setup screen (which
    # integration_enabled=False would trigger) would be unactionable.
    assert integration_enabled is True
    assert "signed in" in detail
    assert "OAuth integrations" in detail
    assert "Visitor API Key" not in detail


def test_resolve_visitor_scopes_to_the_viewer_with_a_token():
    scoped = _FakeClient()
    client, integration_enabled, detail = helpers.resolve_visitor_client(
        _FakeClient(scoped=scoped), True, "tok"
    )
    assert client is scoped
    assert (integration_enabled, detail) == (True, None)


def test_resolve_visitor_gives_the_scoped_client_a_request_deadline():
    # The exchange builds a fresh client with its own session, so the deadline the
    # deploy client carries doesn't come with it; without this the viewer-scoped
    # calls (which is all of them) would be the ones that can hang a thread.
    scoped = _FakeClient()
    client, _, _ = helpers.resolve_visitor_client(
        _FakeClient(scoped=scoped), True, "tok"
    )
    assert set(client.session.adapters) == {"http://", "https://"}
    for adapter in client.session.adapters.values():
        assert isinstance(adapter, helpers._TimeoutAdapter)


def test_resolve_visitor_missing_integration_requires_setup():
    c = _FakeClient(raises=_FakeError(error_code=212))
    assert helpers.resolve_visitor_client(c, True, "tok") == (c, False, None)


def test_resolve_visitor_missing_integration_string_code_requires_setup():
    # The code may arrive as a string; it must still be treated as missing-integration
    # (setup screen) rather than surfaced as an error.
    c = _FakeClient(raises=_FakeError(error_code="212"))
    assert helpers.resolve_visitor_client(c, True, "tok") == (c, False, None)


def test_resolve_visitor_other_error_is_surfaced(capsys):
    c = _FakeClient(raises=_FakeError(error_code=5, error_message="permission denied"))
    assert helpers.resolve_visitor_client(c, True, "tok") == (
        c,
        True,
        helpers.EXCHANGE_FAILED_DETAIL,
    )
    # The technical detail isn't shown to the viewer (it may be full of SDK/vendor
    # detail they can't act on), so it goes to the log for an administrator instead.
    assert "permission denied" in capsys.readouterr().out


def test_resolve_visitor_error_without_a_message_still_says_something(capsys):
    # Not every failure is a ClientError with error_message; the viewer must still
    # be told why rather than getting an empty error screen.
    c = _FakeClient(raises=RuntimeError("connection refused"))
    assert helpers.resolve_visitor_client(c, True, "tok") == (
        c,
        True,
        helpers.EXCHANGE_FAILED_DETAIL,
    )
    assert "connection refused" in capsys.readouterr().out


def test_the_two_session_failures_are_told_apart():
    # A missing integration is actionable on the Access tab, so it keeps the setup
    # screen; a missing session is not, so it must not be reported the same way.
    missing_integration = helpers.resolve_visitor_client(
        _FakeClient(raises=_FakeError(error_code=212)), True, "tok"
    )
    no_session = helpers.resolve_visitor_client(_FakeClient(), True, None)
    assert missing_integration[1] is False and missing_integration[2] is None
    assert no_session[1] is True and no_session[2] is not None


# --- time_since_deployment -------------------------------------------------


def test_time_since_deployment_none_and_empty():
    assert helpers.time_since_deployment(None) == ""
    assert helpers.time_since_deployment("") == ""


def test_time_since_deployment_malformed_returns_empty():
    # A malformed timestamp must not raise (it would otherwise crash the whole
    # content list); it just omits the "last deployed" phrase.
    assert helpers.time_since_deployment("not-a-date") == ""


def test_time_since_deployment_non_string_returns_empty():
    # Anything that isn't a string has no .replace(); it must degrade, not raise.
    assert helpers.time_since_deployment(1750000000) == ""
    assert helpers.time_since_deployment(["2026-01-01"]) == ""


def test_time_since_deployment_naive_timestamp_does_not_crash(frozen_now):
    # A timezone-naive but otherwise valid timestamp must be treated as UTC rather
    # than raising when subtracted from an aware "now".
    naive = (FROZEN_NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    assert helpers.time_since_deployment(naive) == "last deployed 2 hours ago"


def test_time_since_deployment_future(frozen_now):
    assert helpers.time_since_deployment(ago(hours=-1)) == "last deployed in the future"


def test_time_since_deployment_plural_units(frozen_now):
    assert (
        helpers.time_since_deployment(ago(seconds=5)) == "last deployed 5 seconds ago"
    )
    assert (
        helpers.time_since_deployment(ago(minutes=5)) == "last deployed 5 minutes ago"
    )
    assert helpers.time_since_deployment(ago(hours=2)) == "last deployed 2 hours ago"
    assert helpers.time_since_deployment(ago(days=3)) == "last deployed 3 days ago"
    assert helpers.time_since_deployment(ago(days=20)) == "last deployed 2 weeks ago"
    assert helpers.time_since_deployment(ago(days=95)) == "last deployed 3 months ago"
    assert helpers.time_since_deployment(ago(days=800)) == "last deployed 2 years ago"


def test_time_since_deployment_singular_units(frozen_now):
    # Every unit has its own singular form, so every unit needs pinning.
    assert helpers.time_since_deployment(ago(seconds=1)) == "last deployed 1 second ago"
    assert (
        helpers.time_since_deployment(ago(seconds=90)) == "last deployed 1 minute ago"
    )
    assert helpers.time_since_deployment(ago(hours=1)) == "last deployed 1 hour ago"
    assert helpers.time_since_deployment(ago(days=1)) == "last deployed 1 day ago"
    assert helpers.time_since_deployment(ago(days=7)) == "last deployed 1 week ago"
    assert helpers.time_since_deployment(ago(days=45)) == "last deployed 1 month ago"
    assert helpers.time_since_deployment(ago(days=400)) == "last deployed 1 year ago"


def test_time_since_deployment_unit_boundaries(frozen_now):
    # Each threshold rolls over to the next unit exactly once, so an off-by-one in
    # any boundary shows up here.
    assert (
        helpers.time_since_deployment(ago(seconds=59)) == "last deployed 59 seconds ago"
    )
    assert (
        helpers.time_since_deployment(ago(seconds=60)) == "last deployed 1 minute ago"
    )
    assert (
        helpers.time_since_deployment(ago(minutes=59)) == "last deployed 59 minutes ago"
    )
    assert helpers.time_since_deployment(ago(minutes=60)) == "last deployed 1 hour ago"
    assert helpers.time_since_deployment(ago(hours=23)) == "last deployed 23 hours ago"
    assert helpers.time_since_deployment(ago(hours=24)) == "last deployed 1 day ago"
    assert helpers.time_since_deployment(ago(days=6)) == "last deployed 6 days ago"
    assert (
        helpers.time_since_deployment(ago(seconds=0)) == "last deployed 0 seconds ago"
    )


# --- is_chattable_content --------------------------------------------------


def test_chattable_modes_are_the_four_static_modes():
    # Pin the list itself: dropping a mode would silently hide that content type.
    assert set(helpers.CHATTABLE_APP_MODES) == {
        "jupyter-static",
        "quarto-static",
        "rmd-static",
        "static",
    }


@pytest.mark.parametrize(
    "mode", ["static", "quarto-static", "rmd-static", "jupyter-static"]
)
def test_is_chattable_content_accepts_every_static_mode(mode):
    assert helpers.is_chattable_content(make_item(app_mode=mode)) is True


def test_is_chattable_content_rejects_interactive_apps():
    assert helpers.is_chattable_content(make_item(app_mode="python-shiny")) is False


def test_is_chattable_content_rejects_unpublished_and_pins():
    assert helpers.is_chattable_content(make_item(app_role="none")) is False
    assert helpers.is_chattable_content(make_item(content_category="pin")) is False


# --- content_choice_label --------------------------------------------------


def test_content_choice_label_full(frozen_now):
    label = helpers.content_choice_label(make_item())
    assert label == "The Title - Ada Lovelace last deployed 2 hours ago"


def test_content_choice_label_falls_back_to_name_then_guid():
    assert helpers.content_choice_label(make_item(title=None)).startswith("the-name")
    assert helpers.content_choice_label(make_item(title=None, name=None)).startswith(
        "g1"
    )


def test_content_choice_label_tolerates_missing_owner_and_date():
    label = helpers.content_choice_label(make_item(owner=None, last_deployed_time=None))
    # No owner and no deploy time -> just the title, no dangling " - ".
    assert label == "The Title"


def test_content_choice_label_handles_blank_owner_names():
    label = helpers.content_choice_label(
        make_item(
            owner={"first_name": None, "last_name": None},
            last_deployed_time=None,
        )
    )
    assert label == "The Title"


def test_content_choice_label_with_owner_but_no_date():
    assert (
        helpers.content_choice_label(make_item(last_deployed_time=None))
        == "The Title - Ada Lovelace"
    )


def test_content_choice_label_with_date_but_no_owner(frozen_now):
    assert helpers.content_choice_label(make_item(owner=None)) == (
        "The Title - last deployed 2 hours ago"
    )


def test_helpers_tolerate_content_missing_every_optional_field():
    # Connect omits optional fields, and the SDK raises when one is read as an
    # attribute. One unusual item must not be able to empty the whole selector.
    bare = ContentItem(_FakeContext(), guid="g9")
    assert helpers.is_chattable_content(bare) is False
    assert helpers.content_choice_label(bare) == "g9"


# --- truncate_for_context --------------------------------------------------


def test_truncate_for_context_leaves_short_content_untouched():
    text = "a" * 100
    assert helpers.truncate_for_context(text, max_chars=1000) == text


def test_truncate_for_context_keeps_exactly_the_limit():
    result = helpers.truncate_for_context("a" * 5000, max_chars=1000)
    assert result.startswith("a" * 1000)
    # Exactly max_chars of content, not merely "fewer than we started with".
    assert not result.startswith("a" * 1001)
    assert "truncated" in result


def test_truncate_for_context_closes_a_code_fence_it_cut_open():
    # Cutting inside a fenced block would leave the notice below inside the block,
    # where the model reads it as more code rather than as a note about the content.
    result = helpers.truncate_for_context("```python\n" + "x = 1\n" * 500, max_chars=50)
    assert result.count("```") % 2 == 0
    assert "\n```\n\n[Content truncated" in result


def test_truncate_for_context_leaves_balanced_fences_alone():
    result = helpers.truncate_for_context(
        "```\ncode\n```\n" + "a" * 5000, max_chars=1000
    )
    assert result.count("```") == 2


def test_truncate_for_context_ignores_a_fence_mentioned_mid_line():
    # markdownify copies <pre> bodies verbatim, so a page that documents markdown can
    # contain ``` inside an already-closed block. Counting those would "close" the
    # block a second time and push the notice inside the new one.
    body = "x" * 40 + "\n```text\nTo make a code block write ```\nlike that\n```\n"
    result = helpers.truncate_for_context(body + "y" * 200, max_chars=len(body))
    assert result.endswith("]")
    # The notice must sit outside any block: an even number of fence lines precede it.
    before_notice = result.split("\n\n[Content truncated")[0]
    fence_lines = sum(
        1 for line in before_notice.splitlines() if line.lstrip().startswith("```")
    )
    assert fence_lines % 2 == 0


def test_context_limit_is_the_documented_100k():
    # The README tells people to tune this, so the shipped value is pinned.
    assert helpers.MAX_CONTEXT_CHARS == 100_000


def test_truncate_for_context_applies_the_limit_by_default():
    # The default is what production uses; the explicit-max_chars tests above
    # would pass even if it were wrong.
    limit = helpers.MAX_CONTEXT_CHARS
    assert helpers.truncate_for_context("a" * limit) == "a" * limit
    over = helpers.truncate_for_context("a" * (limit + 1))
    assert over.startswith("a" * limit)
    assert not over.startswith("a" * (limit + 1))
    assert "truncated" in over


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


# --- with_request_timeout --------------------------------------------------


def test_with_request_timeout_mounts_on_both_schemes():
    client = _FakeClient()
    assert helpers.with_request_timeout(client) is client
    assert set(client.session.adapters) == {"http://", "https://"}


def test_timeout_adapter_supplies_the_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        helpers.requests.adapters.HTTPAdapter,
        "send",
        lambda self, request, **kwargs: seen.update(kwargs),
    )

    helpers._TimeoutAdapter().send(None, timeout=None)

    assert seen["timeout"] == helpers.CONNECT_REQUEST_TIMEOUT_SECONDS


def test_timeout_adapter_leaves_an_explicit_timeout_alone(monkeypatch):
    # requests passes a caller's own timeout through this same path; the default is
    # a floor for calls that set none, not an override.
    seen = {}
    monkeypatch.setattr(
        helpers.requests.adapters.HTTPAdapter,
        "send",
        lambda self, request, **kwargs: seen.update(kwargs),
    )

    helpers._TimeoutAdapter().send(None, timeout=5)

    assert seen["timeout"] == 5
