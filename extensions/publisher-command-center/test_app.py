# Backend tests for the Publisher Command Center API.
#
# app.py builds a Connect client at import time, which reads CONNECT_SERVER and
# CONNECT_API_KEY from the environment, so set placeholders before importing it.
# The client makes no network call at construction; every test replaces
# `get_visitor_client` (or `client`) with a mock, so no request ever leaves the
# process.
import os
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from posit.connect.errors import ClientError

os.environ.setdefault("CONNECT_SERVER", "https://connect.example.com")
os.environ.setdefault("CONNECT_API_KEY", "placeholder-not-used")

import app  # noqa: E402


def make_client_error(code, http_status=400, message="Server error"):
    return ClientError(code, message, http_status, "Connect returned an error")


async def _noop_sleep(*args, **kwargs):
    pass


class FakeJob(dict):
    # A posit-sdk job is dict-like (job["status"]) and can be destroyed.
    def destroy(self):
        pass


class FakeContent(dict):
    # Stand-in for a posit-sdk ContentItem: a dict (JSON-serializable) that also
    # exposes `app_role` and a `jobs` iterable as attributes.
    def __init__(self, jobs=(), **fields):
        super().__init__(**fields)
        self._jobs = list(jobs)

    @property
    def app_role(self):
        return self["app_role"]

    @property
    def jobs(self):
        return self._jobs


@pytest.fixture
def api():
    return TestClient(app.app)


# --- _connect_http_error ---------------------------------------------------


def test_connect_error_maps_212_to_424():
    exc = app._connect_http_error(make_client_error(212))
    assert isinstance(exc, HTTPException)
    assert exc.status_code == 424
    assert "Visitor API Key" in exc.detail


def test_connect_error_maps_other_to_502():
    exc = app._connect_http_error(make_client_error(5, message="permission denied"))
    assert exc.status_code == 502
    assert exc.detail == "Connect API error: permission denied"


# --- get_visitor_client ----------------------------------------------------


def test_get_visitor_client_maps_setup_error(monkeypatch):
    monkeypatch.setattr(
        app, "_build_visitor_client", MagicMock(side_effect=make_client_error(212))
    )
    with pytest.raises(HTTPException) as excinfo:
        app.get_visitor_client("tok")
    assert excinfo.value.status_code == 424


def test_get_visitor_client_requires_session_on_connect(monkeypatch):
    # On Connect with no session token, don't fall back to the base client.
    monkeypatch.setenv("POSIT_PRODUCT", "CONNECT")
    with pytest.raises(HTTPException) as excinfo:
        app.get_visitor_client(None)
    assert excinfo.value.status_code == 424


def test_get_visitor_client_allows_no_session_off_connect(monkeypatch):
    # Off Connect (local dev) there's no viewer to gate on, so the base client is fine.
    monkeypatch.delenv("POSIT_PRODUCT", raising=False)
    monkeypatch.delenv("RSTUDIO_PRODUCT", raising=False)
    assert app.get_visitor_client(None) is app.client


# --- /api/user -------------------------------------------------------------


def test_user_endpoint_ok(monkeypatch, api):
    visitor = MagicMock()
    visitor.me = {"guid": "u1", "username": "alice", "first_name": "Alice"}
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    resp = api.get("/api/user")

    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


def test_user_endpoint_setup_required(monkeypatch, api):
    def boom(token):
        raise app._connect_http_error(make_client_error(212))

    monkeypatch.setattr(app, "get_visitor_client", boom)
    assert api.get("/api/user").status_code == 424


# --- /api/contents ---------------------------------------------------------


def test_contents_filters_and_attaches_active_jobs(monkeypatch, api):
    visitor = MagicMock()
    visitor.content.find.return_value = [
        FakeContent(
            guid="g1",
            app_role="owner",
            jobs=[{"status": 0}, {"status": 1}, {"status": 0}],
        ),
        FakeContent(guid="g2", app_role="editor", jobs=[{"status": 1}]),
        FakeContent(guid="g3", app_role="viewer", jobs=[{"status": 0}]),  # excluded
    ]
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    resp = api.get("/api/contents")

    assert resp.status_code == 200
    data = resp.json()
    guids = {c["guid"] for c in data}
    assert guids == {"g1", "g2"}  # viewer-only content is dropped
    by_guid = {c["guid"]: c for c in data}
    assert len(by_guid["g1"]["active_jobs"]) == 2  # only status == 0
    assert by_guid["g2"]["active_jobs"] == []


def test_contents_scopes_to_owned_or_collaborated_regardless_of_global_role(
    monkeypatch, api
):
    # Listing is keyed off each item's app_role (the signed-in viewer's relationship
    # to that content), never the viewer's global role. owner/editor are shown;
    # viewer is not; "none" (content an administrator may only oversee, not
    # collaborate on) is also dropped, so an admin sees their own managed content,
    # not a server-wide view.
    visitor = MagicMock()
    visitor.content.find.return_value = [
        FakeContent(guid="own", app_role="owner"),
        FakeContent(guid="collab", app_role="editor"),
        FakeContent(guid="readonly", app_role="viewer"),  # excluded
        FakeContent(guid="admin-oversight", app_role="none"),  # excluded
    ]
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    resp = api.get("/api/contents")

    assert resp.status_code == 200
    assert {c["guid"] for c in resp.json()} == {"own", "collab"}


def test_contents_per_item_job_error_is_isolated(monkeypatch, api):
    class Boom(FakeContent):
        @property
        def jobs(self):
            raise RuntimeError("jobs unavailable")

    visitor = MagicMock()
    visitor.content.find.return_value = [
        Boom(guid="bad", app_role="owner"),
        FakeContent(guid="ok", app_role="owner", jobs=[{"status": 0}]),
    ]
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    resp = api.get("/api/contents")

    assert resp.status_code == 200
    by_guid = {c["guid"]: c for c in resp.json()}
    # None (not []) so the UI can tell "couldn't determine" from a real "0 running".
    assert by_guid["bad"]["active_jobs"] is None  # one bad item doesn't fail the list
    assert len(by_guid["ok"]["active_jobs"]) == 1


def test_contents_setup_required(monkeypatch, api):
    def boom(token):
        raise app._connect_http_error(make_client_error(212))

    monkeypatch.setattr(app, "get_visitor_client", boom)
    assert api.get("/api/contents").status_code == 424


def test_contents_upstream_error_is_502(monkeypatch, api):
    visitor = MagicMock()
    visitor.content.find.side_effect = make_client_error(5)
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    assert api.get("/api/contents").status_code == 502


def test_unexpected_error_becomes_502(monkeypatch):
    # A non-ClientError (e.g. a network failure) is turned into a 502 with a
    # curated message by the global handler, not a bare 500.
    visitor = MagicMock()
    visitor.content.find.side_effect = RuntimeError("network down")
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    # raise_server_exceptions=False so the client returns the handler's response,
    # like a real HTTP client would, instead of re-raising the exception.
    client = TestClient(app.app, raise_server_exceptions=False)
    resp = client.get("/api/contents")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Connect API error. Please try again."


# --- /api/contents/{id} ----------------------------------------------------


def test_content_detail_ok(monkeypatch, api):
    visitor = MagicMock()
    visitor.content.get.return_value = {"guid": "g1", "title": "Report"}
    monkeypatch.setattr(app, "get_visitor_client", lambda token: visitor)

    resp = api.get("/api/contents/g1")

    assert resp.status_code == 200
    assert resp.json()["title"] == "Report"
    visitor.content.get.assert_called_once_with("g1")


# --- destroy_process -------------------------------------------------------


def _visitor_with_content(content):
    visitor = MagicMock()
    visitor.content.get.return_value = content
    return visitor


def test_destroy_process_success(monkeypatch, api):
    content = MagicMock()
    # First find returns the running job (to destroy); the poll then sees it stopped.
    content.jobs.find.side_effect = [FakeJob(status=0), FakeJob(status=3)]
    monkeypatch.setattr(
        app, "get_visitor_client", lambda token: _visitor_with_content(content)
    )

    resp = api.delete("/api/contents/c1/processes/p1")

    assert resp.status_code == 200


def test_destroy_process_not_found_is_ok(monkeypatch, api):
    # The job is already gone; stopping it is a no-op success, not an error.
    content = MagicMock()
    content.jobs.find.return_value = None
    monkeypatch.setattr(
        app, "get_visitor_client", lambda token: _visitor_with_content(content)
    )

    assert api.delete("/api/contents/c1/processes/p1").status_code == 200


def test_destroy_process_still_running_returns_504(monkeypatch, api):
    # The job never stops within the poll window: report it instead of a false 200.
    content = MagicMock()
    content.jobs.find.return_value = FakeJob(status=0)  # always still running
    monkeypatch.setattr(app.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(
        app, "get_visitor_client", lambda token: _visitor_with_content(content)
    )

    resp = api.delete("/api/contents/c1/processes/p1")

    assert resp.status_code == 504
    assert "didn't stop" in resp.json()["detail"]


# --- /api/visitor-auth (bootstrap authorization check) ---------------------


def test_visitor_auth_unauthorized_without_session_on_connect(monkeypatch, api):
    monkeypatch.setenv("POSIT_PRODUCT", "CONNECT")
    resp = api.get("/api/visitor-auth")
    assert resp.status_code == 200
    assert resp.json() == {"authorized": False}


def test_visitor_auth_unauthorized_when_integration_missing(monkeypatch, api):
    monkeypatch.setenv("POSIT_PRODUCT", "CONNECT")
    monkeypatch.setattr(
        app, "_build_visitor_client", MagicMock(side_effect=make_client_error(212))
    )
    resp = api.get("/api/visitor-auth", headers={"Posit-Connect-User-Session-Token": "t"})
    assert resp.json() == {"authorized": False}


def test_visitor_auth_authorized_off_connect(monkeypatch, api):
    monkeypatch.delenv("POSIT_PRODUCT", raising=False)
    monkeypatch.delenv("RSTUDIO_PRODUCT", raising=False)
    assert api.get("/api/visitor-auth").json() == {"authorized": True}


def test_data_endpoint_requires_session_on_connect(monkeypatch, api):
    # The gate protects data endpoints too: no session -> setup, not the base client.
    monkeypatch.setenv("POSIT_PRODUCT", "CONNECT")
    assert api.get("/api/contents").status_code == 424
