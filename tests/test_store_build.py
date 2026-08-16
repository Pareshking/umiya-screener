import pandas as pd
import pytest

from backend.app import service


def _sample_metric_frame():
    return pd.DataFrame([
        {"Symbol": "AAA", "Company Name": "AAA Ltd", "Industry": "Finance", "Index": "NIFTY 50", "Rank": 1, "Momentum Score": 90.0},
        {"Symbol": "BBB", "Company Name": "BBB Ltd", "Industry": "IT", "Index": "NIFTY NEXT 50", "Rank": 2, "Momentum Score": 80.0},
        {"Symbol": "CCC", "Company Name": "CCC Ltd", "Industry": "Finance", "Index": "NIFTY MIDCAP 150", "Rank": 3, "Momentum Score": 70.0},
    ])


def test_api_store_is_read_only_and_uses_persistent_metric_cache(monkeypatch, tmp_path):
    cache = tmp_path / "metrics.parquet"
    frame = _sample_metric_frame()
    frame.to_parquet(cache, index=False)
    monkeypatch.setattr(service, "METRICS_ROOT", tmp_path / "no_metric_versions")
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", cache)

    store = service.ScreenerStore()
    loaded = store.get()
    assert loaded["Symbol"].tolist() == ["AAA", "BBB", "CCC"]
    assert loaded["Momentum Score"].tolist() == [90.0, 80.0, 70.0]


def test_api_store_reports_missing_dataset(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "METRICS_ROOT", tmp_path / "missing_versions")
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", tmp_path / "missing.parquet")
    with pytest.raises(service.MetricsCacheUnavailable):
        service.ScreenerStore().get()
