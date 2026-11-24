import storage_utils as su

STORAGE = [
    {
        "content_guid": "pin-1",
        "content_name": "big-pin",
        "content_title": None,
        "owner_username": "ana",
        "app_mode": "static",
        "bundles": {
            "count": 40,
            "bytes_total": 4_000_000_000,
            "bytes_active": 100_000_000,
            "bytes_inactive": 3_900_000_000,
        },
    },
    {
        "content_guid": "app-1",
        "content_name": "dash",
        "content_title": "Dash",
        "owner_username": "bo",
        "app_mode": "python-shiny",
        "bundles": {
            "count": 2,
            "bytes_total": 20_000_000,
            "bytes_active": 10_000_000,
            "bytes_inactive": 10_000_000,
        },
    },
]

CONTENT = [
    {
        "guid": "pin-1",
        "name": "big-pin",
        "title": None,
        "app_mode": "static",
        "content_category": "pin",
        "bundle_retention_limit": None,
        "dashboard_url": "https://connect/connect/#/apps/pin-1",
        "owner": {"username": "ana", "first_name": "Ana", "last_name": "Lee"},
    },
    {
        "guid": "app-1",
        "name": "dash",
        "title": "Dash",
        "app_mode": "python-shiny",
        "content_category": "",
        "bundle_retention_limit": 0,
        "dashboard_url": "https://connect/connect/#/apps/app-1",
        "owner": {"username": "bo"},
    },
    {
        "guid": "empty-1",
        "name": "empty",
        "title": "Never deployed",
        "app_mode": "unknown",
        "content_category": "",
        "bundle_retention_limit": 5,
        "dashboard_url": "",
        "owner": None,
    },
]


def test_build_report_joins_and_sorts():
    df = su.build_report(STORAGE, CONTENT)
    assert list(df["guid"]) == ["pin-1", "app-1", "empty-1"]
    pin = df.iloc[0]
    assert pin["title"] == "big-pin"
    assert pin["type"] == "pin"
    assert pin["owner"] == "Ana Lee (ana)"
    assert pin["total_mb"] == 4000.0
    assert pin["inactive_mb"] == 3900.0
    assert pin["retention_limit"] == "Server default"
    assert df.iloc[1]["type"] == "python-shiny"
    assert df.iloc[1]["retention_limit"] == "Keep all"
    empty = df.iloc[2]
    assert empty["bundles"] == 0 and empty["retention_limit"] == "5"
    assert empty["owner"] == "(deleted user)"


def test_filters():
    df = su.build_report(STORAGE, CONTENT)
    assert list(su.filter_report(df, pins_only=True)["guid"]) == ["pin-1"]
    assert list(su.filter_report(df, types=["python-shiny"])["guid"]) == ["app-1"]
    assert list(su.filter_report(df, search="ANA")["guid"]) == ["pin-1"]
    assert list(su.filter_report(df, sort_by="title")["title"]) == [
        "Dash",
        "Never deployed",
        "big-pin",
    ]


def test_min_inactive_filter():
    df = su.build_report(STORAGE, CONTENT)
    assert list(su.filter_report(df, min_inactive_mb=50)["guid"]) == ["pin-1"]


def test_content_is_trimmed():
    fat = dict(CONTENT[0], description="x" * 10_000, extra_field=1)
    trimmed = su._trim_content(fat)
    assert "description" not in trimmed and "extra_field" not in trimmed
    assert trimmed["content_category"] == "pin"
    assert trimmed["owner"]["username"] == "ana"


def test_cache_reuses_and_updates(monkeypatch):
    calls = []

    def fake_load(client):
        calls.append(1)
        return {}, su.build_report(STORAGE, CONTENT)

    monkeypatch.setattr(su, "load_all", fake_load)
    cache = su.ReportCache(ttl_seconds=600)
    cache.get(None)
    cache.get(None)
    assert len(calls) == 1
    cache.get(None, force=True)
    assert len(calls) == 2
    cache.update_retention(["pin-1"], "3")
    _, df, _ = cache.current()
    assert df.set_index("guid").loc["pin-1", "retention_limit"] == "3"


def test_format_bytes():
    assert su.format_bytes(0) == "0 B"
    assert su.format_bytes(1_500) == "1.5 KB"
    assert su.format_bytes(3_900_000_000) == "3.9 GB"


def test_csv_has_exact_bytes():
    csv = su.to_csv(su.build_report(STORAGE, CONTENT))
    header = csv.splitlines()[0].split(",")
    assert "total_bytes" in header and "inactive_bytes" in header
    assert "4000000000" in csv


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


class FakeClient:
    def __init__(self):
        self.patches = []

    def get(self, path, params=None):
        if path == "v1/content/storage":
            page = params["page_number"]
            return FakeResponse(
                {"results": [STORAGE[page - 1]], "current_page": page, "total": 2, "total_pages": 2}
            )
        if path == "v1/content":
            return FakeResponse(CONTENT)
        if path == "v1/system/storage":
            return FakeResponse({"bundles": {"bytes_total": 1}})
        raise AssertionError(path)

    def patch(self, path, json=None):
        self.patches.append((path, json))


def test_fetch_content_storage_paginates():
    assert [s["content_guid"] for s in su.fetch_content_storage(FakeClient())] == [
        "pin-1",
        "app-1",
    ]


def test_load_all():
    totals, df = su.load_all(FakeClient())
    assert totals == {"bytes_total": 1}
    assert len(df) == 3


def test_set_retention_limit_sends_null_for_default():
    c = FakeClient()
    su.set_retention_limit(c, "pin-1", None)
    su.set_retention_limit(c, "pin-1", 3)
    assert c.patches == [
        ("v1/content/pin-1", {"bundle_retention_limit": None}),
        ("v1/content/pin-1", {"bundle_retention_limit": 3}),
    ]
