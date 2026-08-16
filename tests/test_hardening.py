import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.data import eligible_symbols
from src.storage import publish_pointer


def test_price_volume_freshness_is_checked_separately():
    dates = pd.bdate_range("2026-02-23", periods=130)
    close = pd.DataFrame({"GOOD": np.arange(130, dtype=float) + 100, "STALE_VOLUME": np.arange(130, dtype=float) + 100}, index=dates)
    volume = pd.DataFrame({"GOOD": np.full(130, 100000.0), "STALE_VOLUME": np.full(130, 100000.0)}, index=dates)
    volume.loc[dates[-5]:, "STALE_VOLUME"] = np.nan
    result = eligible_symbols(close, volume=volume, as_of=dates[-1])
    assert set(result["Symbol"]) == {"GOOD"}


def test_price_only_eligibility_remains_backward_compatible():
    dates = pd.bdate_range("2026-02-23", periods=130)
    close = pd.DataFrame({"AAA": np.arange(130, dtype=float) + 100}, index=dates)
    result = eligible_symbols(close, as_of=dates[-1])
    assert set(result["Symbol"]) == {"AAA"}


def test_publish_pointer_uses_read_pointer_json_contract(monkeypatch):
    captured = {}

    class Body:
        def encode(self, encoding):
            return encoding

    class Client:
        def put_object(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    publish_pointer(object(), "pointers/latest.json", "datasets/dataset_123")
    assert json.loads(captured["Body"].decode("utf-8")) == {"prefix": "datasets/dataset_123"}
    assert captured["ContentType"] == "application/json"
