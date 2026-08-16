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
    high = close * 1.01
    low = close * 0.99
    volume = pd.DataFrame(100000, index=dates, columns=symbols)
    return close, high, low, volume


def test_momentum_shape_and_finiteness():
    close, *_ = sample_data()
    score = momentum_score(close)
    assert score.shape == close.shape
    assert score.iloc[-1].notna().any()


def test_technical_snapshot():
    close, high, low, volume = sample_data()
    out = technical_snapshot(close, high, low, volume)
    assert len(out) == 5
    assert {"CMP", "EMA 50", "EMA 200", "ATR", "ATR %"}.issubset(out.columns)
    assert np.isfinite(out["CMP"]).all()


def test_industry_relative():
    scores = pd.Series([1.0, 2.0, 3.0], index=["AAA", "BBB", "CCC"])
    universe = pd.DataFrame({"Symbol": ["AAA", "BBB", "CCC"], "Industry": ["A", "A", "B"]})
    rel = industry_relative(scores, universe)
    assert rel["AAA"] < 0
    assert rel["BBB"] > 0
    assert rel["CCC"] == 0


def test_acceleration():
    close, *_ = sample_data()
    accel = momentum_acceleration(close)
    assert len(accel) == close.shape[1]
