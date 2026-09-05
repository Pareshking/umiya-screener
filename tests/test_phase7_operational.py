import pandas as pd
from fastapi.testclient import TestClient

from backend.app import main


def ready_frame():
    return pd.DataFrame([
        {"Symbol": "AAA", "Company Name": "AAA Ltd", "Industry": "Finance", "Index": "NIFTY 50", "Rank": 1, "Momentum Score": 90.0, "Market As Of": pd.Timestamp("2026-08-14")},
    ])


def test_liveness_does_not_require_dataset():
    client = TestClient(main.app)
    response = client.get("/api/v1/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-request-id"]


def test_readiness_returns_503_when_metrics_are_unavailable(monkeypatch):
    def unavailable():
        raise main.MetricsCacheUnavailable("metrics unavailable")

    monkeypatch.setattr(main.store, "get", unavailable)
    client = TestClient(main.app)
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "not_ready"
    assert response.headers["x-request-id"]


def test_readiness_reports_dataset_state(monkeypatch):
    frame = ready_frame()
    monkeypatch.setattr(main.store, "get", lambda: frame.copy())
    monkeypatch.setattr(main.store, "_built_at", pd.Timestamp("2026-08-15", tz="UTC").to_pydatetime())
    client = TestClient(main.app)
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["rows"] == 1
    assert body["market_as_of"] == "2026-08-14"
    assert body["data_contract"] == ["adj_close", "volume"]


def test_oversized_request_is_rejected():
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/screener/query",
        content=b"x" * (256 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body is too large."
    assert response.headers["x-request-id"]


def test_dataset_reads_are_cacheable_and_probes_are_not(monkeypatch):
    """Probes report live state, so they stay uncached.

    The published dataset only changes once per scheduled refresh, so the reads
    that serve it carry a short shared cache instead: repeat views then skip a
    full origin round trip, which matters because the origin sleeps on idle.
    """
    frame = ready_frame()
    monkeypatch.setattr(main.store, "get", lambda: frame.copy())
    monkeypatch.setattr(main.store, "_built_at", pd.Timestamp("2026-08-15", tz="UTC").to_pydatetime())
    client = TestClient(main.app)

    response = client.get("/api/v1/screener/metadata")
    assert response.status_code == 200
    assert response.headers["cache-control"] == main.DATASET_CACHE_CONTROL

    for path in ("/api/v1/live", "/api/v1/health"):
        assert client.get(path).headers["cache-control"] == "no-store", path

    # Anything not explicitly marked cacheable must still default to no-store.
    query = client.post("/api/v1/screener/query", json={"filters": [], "sort": {"field": "Rank", "direction": "asc"}, "page": 1, "page_size": 10})
    assert query.headers["cache-control"] == "no-store"
