import numpy as np
import pandas as pd

from src.quant import industry_relative, momentum_acceleration, momentum_score, technical_snapshot


def sample_data():
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-02", periods=400)
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    base = rng.normal(0.0004, 0.015, (400, 5))
    prices = 100 * np.exp(np.cumsum(base, axis=0))
    close = pd.DataFrame(prices, index=dates, columns=symbols)
    volume = pd.DataFrame(100000, index=dates, columns=symbols)
    return close, volume


def test_momentum_shape_and_finiteness():
    close, _ = sample_data()
    score = momentum_score(close)
    assert score.shape == close.shape
    assert score.iloc[-1].notna().any()


def test_technical_snapshot_uses_only_canonical_fields():
    close, volume = sample_data()
    out = technical_snapshot(close, volume)
    assert len(out) == 5
    assert {"CMP", "EMA 50", "EMA 200", "52W High", "Volume Ratio"}.issubset(out.columns)
    assert "ATR" not in out.columns
    assert np.isfinite(out["CMP"]).all()


def test_industry_relative():
    scores = pd.Series([1.0, 2.0, 3.0], index=["AAA", "BBB", "CCC"])
    universe = pd.DataFrame({"Symbol": ["AAA", "BBB", "CCC"], "Industry": ["A", "A", "B"]})
    rel = industry_relative(scores, universe)
    assert rel["AAA"] < 0
    assert rel["BBB"] > 0
    assert rel["CCC"] == 0


def test_acceleration():
    close, _ = sample_data()
    accel = momentum_acceleration(close)
    assert len(accel) == close.shape[1]


def test_clean_prices_preserves_partial_missing_data():
    close, _ = sample_data()
    bad = close.copy()
    bad.iloc[10, :] = np.nan
    bad.iloc[11, :4] = np.nan
    from src.quant import clean_prices
    cleaned = clean_prices(bad)
    assert bad.index[10] in cleaned.index
    assert bad.index[11] in cleaned.index
    assert cleaned.iloc[11].isna().sum() == 4
