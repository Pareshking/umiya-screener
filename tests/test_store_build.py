import numpy as np
import pandas as pd

from backend.app import service


def test_store_builds_expected_metric_table(monkeypatch, tmp_path):
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

    monkeypatch.setattr(service, "load_universe", lambda: universe.copy())
    monkeypatch.setattr(service, "fetch_ohlcv", lambda symbols, period="2y": {
        "close": close, "high": high, "low": low, "volume": volume,
    })
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", tmp_path / "metrics.parquet")

    store = service.ScreenerStore()
    frame = store.get(force=True)

    assert len(frame) == 3
    assert set(["Momentum Score", "Acceleration", "3M Sharpe", "6M Sharpe", "R² 1Y", "Rank"]).issubset(frame.columns)
    assert frame["Rank"].notna().all()
    assert frame["CMP"].notna().all()
    assert (tmp_path / "metrics.parquet").exists()
