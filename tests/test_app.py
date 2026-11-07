from fastapi.testclient import TestClient

from agriconnect.app import create_app
from agriconnect.catalogue import load
from agriconnect.policy import Dataset

from .test_policy import ds


class Fake:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def aggregate(self, d, dims, measure, limit):
        self.calls += 1
        return self.rows


def client(datasets, rows=None, token="t0k"):
    src = Fake(rows or [])
    app = create_app(datasets, src, token=lambda: token)
    return TestClient(app), src


AUTH = {"Authorization": "Bearer t0k"}
Q = "/v1/datasets/rain/series?dims=district&measure=rainfall_mm"


def test_health_needs_no_token_everything_else_does():
    c, _ = client({"rain": ds()})
    assert c.get("/health").status_code == 200
    assert c.get("/v1/datasets").status_code == 401
    assert c.get(Q).status_code == 401
    assert c.get("/v1/datasets", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_a_service_with_no_token_configured_answers_nothing():
    c, src = client({"rain": ds()}, token=None)
    assert c.get("/v1/datasets", headers=AUTH).status_code == 503
    assert c.get(Q, headers=AUTH).status_code == 503
    assert src.calls == 0


def test_only_eligible_datasets_are_listed_and_ineligible_ones_do_not_exist():
    off = ds(id="off", enabled=False)
    c, src = client({"rain": ds(), "off": off})
    ids = [d["id"] for d in c.get("/v1/datasets", headers=AUTH).json()["datasets"]]
    assert ids == ["rain"]
    r = c.get("/v1/datasets/off/series?dims=district&measure=rainfall_mm", headers=AUTH)
    assert r.status_code == 404
    assert src.calls == 0


def test_a_series_is_aggregated_floored_and_labelled_with_its_licence():
    rows = [{"district": "a", "n": 3, "mean": 1.0}, {"district": "b", "n": 25, "mean": 2.0}]
    c, _ = client({"rain": ds()}, rows)
    j = c.get(Q, headers=AUTH).json()
    assert j["licence"] == "CC-BY-4.0"
    assert [r["district"] for r in j["rows"]] == ["b"]


def test_private_columns_are_refused_before_the_source_is_touched():
    c, src = client({"rain": ds()}, [{"station_id": "s1", "n": 99}])
    r = c.get("/v1/datasets/rain/series?dims=station_id&measure=rainfall_mm", headers=AUTH)
    assert r.status_code == 400
    assert src.calls == 0


def test_the_shipped_catalogue_serves_nothing_until_the_owner_enables_something():
    catalog = load()
    assert catalog, "the example entry should parse"
    assert not any(
        isinstance(d, Dataset) and d.enabled for d in catalog.values()
    ), "no dataset is enabled in the scaffold"
    c, _ = client(catalog)
    assert c.get("/v1/datasets", headers=AUTH).json() == {"datasets": []}
