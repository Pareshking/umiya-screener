import numpy as np
import pandas as pd

from src.quant import returns, rolling_r2, sharpe, technical_snapshot


def monotonic_data(days=300):
    idx = pd.bdate_range("2025-01-01", periods=days)
    close = pd.DataFrame({"A": np.arange(days, dtype=float) + 100.0}, index=idx)
    volume = pd.DataFrame({"A": 1000.0}, index=idx)
    return close, volume


def test_returns_use_trading_observations():
    close, _ = monotonic_data()
    out = returns(close)
    expected = (close.iloc[-1, 0] / close.iloc[-64, 0] - 1) * 100
    assert np.isclose(out.loc["A", "3M Return"], expected)


def test_12m_return_fallback_is_zero_when_history_is_short():
    close, _ = monotonic_data(200)
    out = returns(close)
    assert out.loc["A", "12M Return"] == 0.0


def test_r2_of_linear_log_price_is_high():
    close, _ = monotonic_data()
    r2 = rolling_r2(close, 252).iloc[-1, 0]
    assert 0.99 <= r2 <= 1.0


def test_sharpe_is_finite_for_nonconstant_price_series():
    close, _ = monotonic_data()
    value = sharpe(close, 63).iloc[-1, 0]
    assert np.isfinite(value)


def test_technical_metrics_have_no_ohlc_dependency():
    close, volume = monotonic_data()
    snapshot = technical_snapshot(close, volume)
    forbidden = {"Open", "High", "Low", "Close", "ATR", "Chandelier Exit"}
    assert forbidden.isdisjoint(snapshot.columns)
    assert snapshot.loc["A", "Within 20% of 52W High"]
