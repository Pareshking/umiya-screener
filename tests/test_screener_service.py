import pandas as pd

from backend.app.schemas import ScreenerQuery
from backend.app.service import query


def test_query_filters_and_paginates(monkeypatch):
    frame = pd.DataFrame([
        {"Symbol":"AAA","Company Name":"AAA Ltd","Industry":"Finance","Index":"NIFTY 50","Rank":1,"Momentum Score":90.0,"3M Return":20.0},
        {"Symbol":"BBB","Company Name":"BBB Ltd","Industry":"IT","Index":"NIFTY NEXT 50","Rank":2,"Momentum Score":80.0,"3M Return":5.0},
        {"Symbol":"CCC","Company Name":"CCC Ltd","Industry":"Finance","Index":"NIFTY MIDCAP 150","Rank":3,"Momentum Score":70.0,"3M Return":-2.0},
    ])
    from backend.app import service
    monkeypatch.setattr(service.store, "get", lambda force=False: frame.copy())
    payload = ScreenerQuery.model_validate({
        "filters":[{"field":"3M Return","operator":">","value":0}],
        "sort":{"field":"Momentum Score","direction":"desc"},
        "page":1,"page_size":1,
    })
    result = query(payload)
    assert result["total"] == 2
    assert len(result["rows"]) == 1
    assert result["rows"][0]["Symbol"] == "AAA"


def test_query_supports_index_membership_filter(monkeypatch):
    frame = pd.DataFrame([
        {"Symbol":"AAA","Index":"NIFTY 50","Rank":1},
        {"Symbol":"BBB","Index":"NIFTY NEXT 50","Rank":2},
        {"Symbol":"CCC","Index":"NIFTY 50","Rank":3},
    ])
    from backend.app import service
    monkeypatch.setattr(service.store, "get", lambda force=False: frame.copy())
    payload = ScreenerQuery.model_validate({
        "filters":[{"field":"Index","operator":"in","value":["NIFTY 50"]}],
        "sort":{"field":"Rank","direction":"asc"},
    })
    result = query(payload)
    assert result["total"] == 2
    assert [row["Symbol"] for row in result["rows"]] == ["AAA", "CCC"]
