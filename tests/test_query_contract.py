import pandas as pd

from backend.app import service


def _frame():
    return pd.DataFrame({
        "Rank": [1, 2, 3, 4],
        "Symbol": ["AAA", "ABCD", "XYZ", "ABC"],
        "Company Name": ["Alpha Motors", "Beta Systems", "XYZ Finance", "Alpha Finance"],
        "Industry": ["Auto", "IT", "Finance", "Finance"],
        "Index": ["NIFTY 50"] * 4,
        "Momentum Score": [90.0, 80.0, 70.0, 60.0],
        "CMP": [100.0, 200.0, 300.0, 400.0],
    })


def test_query_search_matches_symbol_or_company(monkeypatch):
    monkeypatch.setattr(service.store, "get", lambda: _frame())
    payload = type("Payload", (), {
        "search": "alpha",
        "filters": [],
        "sort": type("Sort", (), {"field": "Rank", "direction": "asc"})(),
        "page": 1,
        "page_size": 50,
    })()
    result = service.query(payload)
    assert [row["Symbol"] for row in result["rows"]] == ["AAA", "ABC"]


def test_query_paginates_after_filter_and_sort(monkeypatch):
    monkeypatch.setattr(service.store, "get", lambda: _frame())
    payload = type("Payload", (), {
        "search": None,
        "filters": [],
        "sort": type("Sort", (), {"field": "Momentum Score", "direction": "desc"})(),
        "page": 2,
        "page_size": 2,
    })()
    result = service.query(payload)
    assert result["total"] == 4
    assert result["pages"] == 2
    assert [row["Symbol"] for row in result["rows"]] == ["XYZ", "ABC"]
