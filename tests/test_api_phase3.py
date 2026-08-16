import pandas as pd
from fastapi.testclient import TestClient

from backend.app import main


def sample_frame():
    return pd.DataFrame([
        {"Symbol": "AAA", "Company Name": "AAA Ltd", "Industry": "Finance", "Index": "NIFTY 50", "Rank": 1, "Momentum Score": 90.0, "3M Return": 20.0, "Market As Of": pd.Timestamp("2026-08-14")},
        {"Symbol": "BBB", "Company Name": "BBB Ltd", "Industry": "IT", "Index": "NIFTY NEXT 50", "Rank": 2, "Momentum Score": 80.0, "3M Return": 5.0, "Market As Of": pd.Timestamp("2026-08-14")},
    ])


def install_store(monkeypatch):
    frame = sample_frame()
    monkeypatch.setattr(main.store, "get", lambda: frame.copy())
    monkeypatch.setattr(main.store, "_frame", frame.copy())
    monkeypatch.setattr(main.store, "_built_at", pd.Timestamp("2026-08-15", tz="UTC").to_pydatetime())


def test_query_endpoint_filters_and_paginates(monkeypatch):
    install_store(monkeypatch)
    client = TestClient(main.app)
    response = client.post("/api/v1/screener/query", json={
        "filters": [{"field": "3M Return", "operator": ">", "value": 10}],
        "sort": {"field": "Momentum Score", "direction": "desc"},
        "page": 1,
        "page_size": 1,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["rows"][0]["Symbol"] == "AAA"
    assert body["pages"] == 1


def test_query_endpoint_rejects_unknown_filter_field(monkeypatch):
    install_store(monkeypatch)
    client = TestClient(main.app)
    response = client.post("/api/v1/screener/query", json={
        "filters": [{"field": "Made Up Metric", "operator": ">", "value": 1}],
    })
    assert response.status_code == 400
    assert "Unsupported filter field" in response.json()["detail"]


def test_stock_endpoint_normalizes_yahoo_symbol(monkeypatch):
    install_store(monkeypatch)
    client = TestClient(main.app)
    response = client.get("/api/v1/stocks/AAA.NS")
    assert response.status_code == 200
    assert response.json()["Symbol"] == "AAA"


def test_export_endpoint_returns_csv(monkeypatch):
    install_store(monkeypatch)
    client = TestClient(main.app)
    response = client.post("/api/v1/screener/export", json={"page_size": 50})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Symbol" in response.text
    assert "AAA" in response.text
