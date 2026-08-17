import numpy as np
import pandas as pd

from src.quant import (
    MOMENTUM_WEIGHTS,
    MOMENTUM_WINDOWS,
    eligible_symbols,
    momentum_score,
    returns,
    sharpe,
    technical_snapshot,
)


def monotonic_data(days=320, symbols=("A",)):
    idx = pd.bdate_range("2025-01-01", periods=days)
    t = np.arange(days, dtype=float)
    data = {symbol: np.exp(np.log(100.0 + i * 10) + 0.005 * t) for i, symbol in enumerate(symbols)}
    close = pd.DataFrame(data, index=idx)
    volume = pd.DataFrame(1000.0, index=idx, columns=symbols)
    return close, volume


def test_lookback_contract_is_stable():
    assert MOMENTUM_WINDOWS == (21, 63, 126, 189, 252)
    assert MOMENTUM_WEIGHTS == (0.10, 0.30, 0.30, 0.20, 0.10)
    assert sum(MOMENTUM_WEIGHTS) == 1.0


def test_eligibility_requires_126_valid_observations_without_imputation():
    close, _ = monotonic_data(160, ("GOOD", "SHORT"))
    close.loc[close.index[:35], "SHORT"] = np.nan
    assert list(eligible_symbols(close)) == ["GOOD"]


def test_returns_use_trading_observations():
    close, _ = monotonic_data()
    out = returns(close)
    expected = (close.iloc[-1, 0] / close.iloc[-64, 0] - 1) * 100
    assert np.isclose(out.loc["A", "3M Return"], expected)


def test_12m_return_remains_missing_when_history_is_short():
    close, _ = monotonic_data(126)
    out = returns(close)
    assert pd.isna(out.loc["A", "12M Return"])
    assert pd.isna(out.loc["A", "6M Return"])


def test_12m_return_is_point_to_point_when_history_is_available():
    close, _ = monotonic_data(260)
    out = returns(close)
    expected = (close.iloc[-1, 0] / close.iloc[-253, 0] - 1) * 100
    assert np.isclose(out.loc["A", "12M Return"], expected)


def test_sharpe_matches_annualized_log_return_definition():
    close, _ = monotonic_data()
    t = np.arange(len(close), dtype=float)
    close["A"] *= np.exp(0.001 * np.sin(t / 7.0))
    result = sharpe(close, 126).iloc[-1, 0]
    logret = np.log(close["A"] / close["A"].shift(1))
    expected = np.log(close.iloc[-1, 0] / close.iloc[-127, 0]) / (logret.rolling(126).std().iloc[-1] * np.sqrt(126))
    assert np.isfinite(result)
    assert np.isclose(result, expected, rtol=1e-10, atol=1e-10)


def test_momentum_score_respects_minimum_history():
    close, _ = monotonic_data(320, ("A", "B", "SHORT"))
    close.loc[close.index[:200], "SHORT"] = np.nan
    score = momentum_score(close)
    assert score.shape == close.shape
    assert score["SHORT"].isna().all()
    assert score[["A", "B"]].iloc[-1].notna().all()


def test_technical_metrics_have_no_ohlc_dependency():
    close, volume = monotonic_data()
    snapshot = technical_snapshot(close, volume)
    forbidden = {"Open", "High", "Low", "Close", "ATR", "Chandelier Exit"}
    assert forbidden.isdisjoint(snapshot.columns)
    assert snapshot.loc["A", "Within 20% of 52W High"]
    assert np.isfinite(snapshot.loc["A", "CMP"])
