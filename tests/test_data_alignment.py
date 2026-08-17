import numpy as np
import pandas as pd

from src.quant import clean_prices, momentum_score, returns


def test_clean_prices_never_fills_before_first_real_observation():
    idx = pd.bdate_range("2026-01-01", periods=8)
    close = pd.DataFrame({"NEW": [np.nan, np.nan, 100.0, np.nan, 102.0, np.nan, 104.0, 105.0]}, index=idx)
    cleaned = clean_prices(close)
    assert cleaned.iloc[:2, 0].isna().all()
    assert cleaned.iloc[2:, 0].tolist() == [100.0, 100.0, 102.0, 102.0, 104.0, 105.0]


def test_returns_use_trading_observation_order_after_cleaning():
    idx = pd.bdate_range("2026-01-01", periods=260)
    values = np.arange(260, dtype=float) + 100.0
    values[100] = np.nan
    close = pd.DataFrame({"A": values}, index=idx)
    out = returns(close)
    cleaned = clean_prices(close)
    expected = (cleaned["A"].iloc[-1] / cleaned["A"].iloc[-64] - 1) * 100
    assert np.isclose(out.loc["A", "3M Return"], expected)


def test_pre_listing_history_does_not_create_eligibility_or_momentum():
    idx = pd.bdate_range("2025-01-01", periods=260)
    t = np.arange(260, dtype=float)
    close = pd.DataFrame({
        "OLD": 100.0 * np.exp(0.001 * t),
        "NEW": np.r_[np.full(200, np.nan), 100.0 * np.exp(0.01 * np.arange(60))],
    }, index=idx)
    score = momentum_score(close)
    assert score["NEW"].isna().all()
    assert np.isfinite(score["OLD"].iloc[-1])
