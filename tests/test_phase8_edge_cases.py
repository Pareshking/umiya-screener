import pandas as pd

from backend.app.schemas import ScreenerQuery
from backend.app import service


def _frame():
    return pd.DataFrame([
        {"Symbol": "AAA", "Company Name": "Alpha Motors", "Industry": "Auto", "Index": "NIFTY 50", "Rank": 1, "Momentum Score": 100.0, "3M Return": 25.0},
        {"Symbol": "BBB", "Company Name": "Beta Systems", "Industry": "IT", "Index": "NIFTY NEXT 50", "Rank": 2, "Momentum Score": 80.0, "3M Return": 5.0},
        {"Symbol": "CCC", "Company Name": "Gamma Finance", "Industry": "Finance", "Index": "NIFTY MIDCAP 150", "Rank": 3, "Momentum Score": 60.0, "3M Return": -10.0},
    ])


def test_empty_result_has_stable_pagination_contract(monkeypatch):
    monkeypatch.setattr(service.store, "get", lambda: _frame())
    payload = ScreenerQuery.model_validate({
        "filters": [{"field": "3M Return", "operator": ">", "value": 1000}],
        "sort": {"field": "Momentum Score", "direction": "desc"},
        "page": 1,
        "page_size": 50,
    })
    result = service.query(payload)
    assert result["total"] == 0
    assert result["pages"] == 1
    assert result["rows"] == []


def test_search_filter_sort_and_pagination_are_applied_in_order(monkeypatch):
    monkeypatch.setattr(service.store, "get", lambda: _frame())
    payload = ScreenerQuery.model_validate({
        "search": "a",
        "filters": [{"field": "3M Return", "operator": ">=", "value": -10}],
        "sort": {"field": "Momentum Score", "direction": "desc"},
        "page": 2,
        "page_size": 1,
    })
    result = service.query(payload)
    assert result["total"] == 3
    assert result["pages"] == 3
    assert [row["Symbol"] for row in result["rows"]] == ["BBB"]


def test_missing_numeric_values_are_not_fabricated(monkeypatch):
    frame = _frame()
    frame.loc[1, "3M Return"] = None
    monkeypatch.setattr(service.store, "get", lambda: frame.copy())
    payload = ScreenerQuery.model_validate({
        "filters": [{"field": "3M Return", "operator": ">", "value": 0}],
        "sort": {"field": "3M Return", "direction": "desc"},
    })
    result = service.query(payload)
    assert result["total"] == 1
    assert result["rows"][0]["Symbol"] == "AAA"
    assert all(row["Symbol"] != "BBB" for row in result["rows"])
