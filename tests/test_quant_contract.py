import numpy as np
import pandas as pd
import pytest

from src.calendar_momentum import ANCHOR_STALENESS_LIMIT, calendar_start_positions, latest_as_of_date
from src.quant import (
    MOMENTUM_MONTHS,
    MOMENTUM_WEIGHTS,
    eligible_symbols,
    momentum_score,
    period_window,
    returns,
    sharpe,
    technical_snapshot,
)


def monotonic_data(days=320, symbols=("A",), end="2026-09-01"):
    """Business-day price history ending on a recent date.

    The horizons are calendar periods, so the data must sit on real calendar
    dates rather than an arbitrary start offset.
    """
    idx = pd.bdate_range(end=pd.Timestamp(end), periods=days)
    t = np.arange(days, dtype=float)
    data = {symbol: np.exp(np.log(100.0 + i * 10) + 0.005 * t) for i, symbol in enumerate(symbols)}
    close = pd.DataFrame(data, index=idx)
    volume = pd.DataFrame(1000.0, index=idx, columns=symbols)
    return close, volume


def calendar_anchor(close, months):
    """The observation the calendar window actually opens on."""
    index = pd.DatetimeIndex(close.index)
    starts = calendar_start_positions(index, months, latest_as_of=latest_as_of_date(index))
    return int(starts[-1])


def test_lookback_contract_is_calendar_months():
    assert MOMENTUM_MONTHS == (1, 3, 6, 9, 12)
    assert MOMENTUM_WEIGHTS == (0.10, 0.30, 0.30, 0.20, 0.10)
    assert sum(MOMENTUM_WEIGHTS) == pytest.approx(1.0)


def test_eligibility_requires_126_valid_observations_without_imputation():
    close, _ = monotonic_data(160, ("GOOD", "SHORT"))
    close.loc[close.index[:35], "SHORT"] = np.nan
    assert list(eligible_symbols(close)) == ["GOOD"]


def test_window_is_anchored_to_the_calendar_not_to_a_row_count():
    """A gap in the session grid must not drag the window further back in time.

    This is the whole point of the change. With a fixed 63-row window, losing
    ten sessions to an exchange closure silently pushes the 3M start two weeks
    earlier; with a calendar window the start date stays put and the window
    simply contains fewer observations.
    """
    close, _ = monotonic_data()
    full = period_window(close, 3)
    assert full["reachable"]
    assert full["actual_start"] >= full["target_start"]
    assert full["actual_start"] - full["target_start"] <= pd.Timedelta(days=7)

    # Remove ten sessions from inside the 3M window.
    start = calendar_anchor(close, 3)
    gapped = close.drop(close.index[start + 5:start + 15])
    gapped_window = period_window(gapped, 3)

    assert gapped_window["actual_start"] == full["actual_start"]
    assert gapped_window["observations"] == full["observations"] - 10


def test_returns_are_point_to_point_across_the_calendar_window():
    close, _ = monotonic_data()
    out = returns(close)
    start = calendar_anchor(close, 3)
    expected = (close.iloc[-1, 0] / close.iloc[start, 0] - 1) * 100
    assert np.isclose(out.loc["A", "3M Return"], expected)


def test_12m_return_remains_missing_when_history_is_short():
    close, _ = monotonic_data(126)
    out = returns(close)
    assert pd.isna(out.loc["A", "12M Return"])
    assert pd.isna(out.loc["A", "9M Return"])
    assert np.isfinite(out.loc["A", "3M Return"])


def test_12m_return_is_point_to_point_when_history_is_available():
    close, _ = monotonic_data(400)
    out = returns(close)
    start = calendar_anchor(close, 12)
    expected = (close.iloc[-1, 0] / close.iloc[start, 0] - 1) * 100
    assert np.isclose(out.loc["A", "12M Return"], expected)


def test_sharpe_matches_period_scale_log_return_definition():
    close, _ = monotonic_data()
    t = np.arange(len(close), dtype=float)
    close["A"] *= np.exp(0.001 * np.sin(t / 7.0))
    result = sharpe(close, 6).iloc[-1, 0]

    start = calendar_anchor(close, 6)
    logret = np.log(close["A"] / close["A"].shift(1)).iloc[start + 1:]
    period_vol = logret.std(ddof=0) * np.sqrt(len(logret))
    expected = np.log(close.iloc[-1, 0] / close.iloc[start, 0]) / period_vol
    assert np.isfinite(result)
    assert np.isclose(result, expected, rtol=1e-10, atol=1e-10)


def test_window_anchor_bridges_a_holed_session_but_not_a_suspension():
    close, _ = monotonic_data(400, ("A", "B", "C"))
    start = calendar_anchor(close, 3)
    holed = close.copy()
    holed.iloc[start, 0] = np.nan
    assert np.isfinite(returns(holed).loc["A", "3M Return"])

    suspended = close.copy()
    suspended.iloc[start - 2 * ANCHOR_STALENESS_LIMIT:start + 1, 1] = np.nan
    assert pd.isna(returns(suspended).loc["B", "3M Return"])


def test_momentum_score_respects_minimum_history():
    close, _ = monotonic_data(400, ("A", "B", "SHORT"))
    close.loc[close.index[:280], "SHORT"] = np.nan
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
