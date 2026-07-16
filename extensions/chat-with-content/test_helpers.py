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


# --- time_since_deployment -------------------------------------------------


def test_time_since_deployment_none_and_empty():
    assert helpers.time_since_deployment(None) == ""
    assert helpers.time_since_deployment("") == ""


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
