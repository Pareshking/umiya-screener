import numpy as np
import pandas as pd

from src.quant import clean_prices, momentum_score, returns


def test_clean_prices_never_fills_before_first_real_observation():
    idx = pd.bdate_range("2026-01-01", periods=8)
    close = pd.DataFrame({"NEW": [np.nan, np.nan, 100.0, np.nan, 102.0, np.nan, 104.0, 105.0]}, index=idx)
    cleaned = clean_prices(close)
    assert cleaned.iloc[:2, 0].isna().all()
    assert cleaned.iloc[2:, 0].tolist() == [100.0, 100.0, 102.0, 102.0, 104.0, 105.0]


def test_returns_use_genuine_observation_order_not_calendar_rows():
    idx = pd.bdate_range("2026-01-01", periods=6)
    close = pd.DataFrame({"A": [100.0, 101.0, np.nan, 103.0, 104.0, 105.0]}, index=idx)
    out = returns(close, windows=(2,))
    # After cleaning, the last two observations are 104 -> 105.
    assert np.isclose(out.loc["A", "1M Return"], (105.0 / 103.0 - 1) * 100) is False
    # The function's observation convention uses the value two observations
    # before the latest: 103 -> 105.
    assert np.isclose(out.loc["A", "1M Return"], (105.0 / 103.0 - 1) * 100)


def test_pre_listing_history_does_not_create_eligibility_or_momentum():
    idx = pd.bdate_range("2025-01-01", periods=260)
    t = np.arange(260, dtype=float)
    close = pd.DataFrame({
        "OLD": 100.0 * np.exp(0.001 * t),
        "NEW": np.r_[np.full(200, np.nan), 100.0 * np.exp(0.01 * np.arange(60))],
    }, index=idx)
    score = momentum_score(close)
    assert score["NEW"].isna().all()
    assert score["OLD"].iloc[-1] == score["OLD"].iloc[-1]
