import numpy as np
import pandas as pd
import pytest

from backend.app import service


def _sample_inputs():
    dates = pd.bdate_range("2023-01-02", periods=400)
    symbols = ["AAA", "BBB", "CCC"]
    values = np.arange(len(dates), dtype=float)[:, None] + np.array([100.0, 120.0, 140.0])
    close = pd.DataFrame(values, index=dates, columns=symbols)
    high = close * 1.01
    low = close * 0.99
    volume = pd.DataFrame(100_000.0, index=dates, columns=symbols)
    universe = pd.DataFrame({
        "Symbol": symbols,
        "Company Name": ["AAA Ltd", "BBB Ltd", "CCC Ltd"],
        "Industry": ["Finance", "IT", "Finance"],
        "Index": ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 150"],
    })
    return close, high, low, volume, universe


def test_build_publishes_expected_metric_table(monkeypatch, tmp_path):
    close, high, low, volume, universe = _sample_inputs()
    calls = {"prices": 0}
    monkeypatch.setattr(service, "load_universe", lambda: universe.copy())

    def fake_prices(symbols, period="2y"):
        calls["prices"] += 1
        return {"close": close, "high": high, "low": low, "volume": volume}

    monkeypatch.setattr(service, "fetch_ohlcv", fake_prices)
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", tmp_path / "metrics.parquet")

    frame, built_at = service.build_metric_frame()
    service.write_metric_cache(frame, built_at)

    assert len(frame) == 3
    assert {"Momentum Score", "Acceleration", "3M Sharpe", "6M Sharpe", "R² 1Y", "Rank"}.issubset(frame.columns)
    assert frame["Rank"].notna().all()
    assert frame["CMP"].notna().all()
    assert (tmp_path / "metrics.parquet").exists()
    assert calls["prices"] == 1


def test_api_store_is_read_only_and_uses_persistent_cache(monkeypatch, tmp_path):
    close, high, low, volume, universe = _sample_inputs()
    cache = tmp_path / "metrics.parquet"
    frame = universe.copy()
    frame["Rank"] = [1, 2, 3]
    frame["Momentum Score"] = [90.0, 80.0, 70.0]
    frame.to_parquet(cache, index=False)
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", cache)
    monkeypatch.setattr(service, "fetch_ohlcv", lambda *args, **kwargs: pytest.fail("API must not download prices"))
    monkeypatch.setattr(service, "load_universe", lambda: pytest.fail("API must not rebuild the universe"))

    store = service.ScreenerStore()
    loaded = store.get()
    assert loaded["Symbol"].tolist() == ["AAA", "BBB", "CCC"]


def test_api_store_reports_missing_dataset(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", tmp_path / "missing.parquet")
    with pytest.raises(service.MetricsCacheUnavailable):
        service.ScreenerStore().get()
