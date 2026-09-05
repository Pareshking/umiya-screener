from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .calendar_momentum import (
    ANCHOR_STALENESS_LIMIT,
    calendar_period_metrics,
    calendar_start_positions,
    calendar_targets,
    latest_as_of_date,
    window_is_reachable,
    winsorised_cross_section_z,
)
from .config import DEFAULT_LOOKBACK_WEIGHTS, MIN_HISTORY, MOMENTUM_MONTHS

# Horizons are calendar months (1M/3M/6M/9M/12M), not trading-row counts.
MOMENTUM_MONTHS = tuple(MOMENTUM_MONTHS)
MOMENTUM_WEIGHTS = tuple(DEFAULT_LOOKBACK_WEIGHTS)
PERIOD_LABELS = {1: "1M", 3: "3M", 6: "6M", 9: "9M", 12: "12M"}


def clean_holidays(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Drop dates where more than 70% of the universe has no observation.

    Those rows are market holidays that leaked into the vendor's date grid.
    Keeping them adds nothing and drags every cross-sectional statistic
    computed on that date towards the handful of symbols that did print.
    """
    if frame is None or frame.empty:
        return frame if frame is not None else pd.DataFrame()
    limit = max(int(frame.shape[1] * 0.70), 1)
    return frame.loc[frame.isna().sum(axis=1) <= limit]


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Normalize dates and bridge short gaps after each stock's first observation.

    Values before a stock's first real observation are never imputed, and the
    forward fill is capped at ANCHOR_STALENESS_LIMIT sessions: a genuinely
    suspended stock goes NaN rather than carrying a stale price forward for
    months.
    """
    if prices.empty:
        return prices.copy()
    out = prices.copy()
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out = out.sort_index()
    first_valid = out.notna().idxmax()
    for column in out.columns:
        first = first_valid[column]
        if pd.isna(first):
            continue
        out.loc[first:, column] = out.loc[first:, column].ffill(limit=ANCHOR_STALENESS_LIMIT)
    return out


def _log_returns(close: pd.DataFrame) -> pd.DataFrame:
    return np.log(close / close.shift(1).replace(0, np.nan))


def _last_valid(series: pd.Series) -> float:
    valid = series.dropna()
    return float(valid.iloc[-1]) if not valid.empty else np.nan


def eligible_symbols(prices: pd.DataFrame, min_history: int = MIN_HISTORY) -> pd.Index:
    if prices.empty:
        return pd.Index([], dtype=object)
    return prices.notna().sum(axis=0).loc[lambda s: s >= min_history].index


def period_window(close: pd.DataFrame, months: int) -> dict:
    """Describe the calendar window a horizon actually resolved to.

    Exposed for the audit scripts and the UI: a 12M column is only trustworthy
    if you can see which two dates it spans and how many sessions it covers.
    """
    close = clean_prices(close)
    index = pd.DatetimeIndex(close.index)
    if index.empty:
        return {"months": months, "target_start": pd.NaT, "actual_start": pd.NaT,
                "end": pd.NaT, "as_of": pd.NaT, "observations": 0, "reachable": False}
    as_of = latest_as_of_date(index)
    starts = calendar_start_positions(index, months, latest_as_of=as_of)
    targets = calendar_targets(index, months, latest_as_of=as_of)
    end = len(index) - 1
    start = int(starts[end])
    reachable = window_is_reachable(index, start, targets[end], end)
    return {
        "months": months,
        "target_start": pd.Timestamp(targets[end]),
        "actual_start": pd.Timestamp(index[start]) if start < len(index) else pd.NaT,
        "end": pd.Timestamp(index[end]),
        "as_of": as_of,
        "observations": end - start,
        "reachable": bool(reachable),
    }


def returns(close: pd.DataFrame, months: Sequence[int] = MOMENTUM_MONTHS) -> pd.DataFrame:
    """Point-to-point simple returns over each calendar horizon, in percent."""
    return _returns(clean_prices(close), months)


def _returns(close: pd.DataFrame, months: Sequence[int] = MOMENTUM_MONTHS) -> pd.DataFrame:
    """As :func:`returns`, on an already-cleaned frame.

    ``clean_prices`` is deliberately not idempotent-safe to re-apply: bridging
    a gap twice would stretch the 5-session limit to 10, so every internal
    caller works on a frame that has been cleaned exactly once.
    """
    out = pd.DataFrame(index=close.columns)
    if close.empty:
        for period in months:
            out[f"{PERIOD_LABELS[period]} Return"] = pd.Series(dtype=float)
        return out
    log_ret = _log_returns(close)
    as_of = latest_as_of_date(pd.DatetimeIndex(close.index))
    for period in months:
        _, last_ret, _ = calendar_period_metrics(
            close, log_ret, period, latest_as_of=as_of, anchor_limit=None, last_row_only=True
        )
        out[f"{PERIOD_LABELS[period]} Return"] = last_ret * 100
    return out


def sharpe(close: pd.DataFrame, months: int) -> pd.DataFrame:
    """Period-scale Sharpe over a calendar window of `months` months.

    Cumulative log return across the window divided by that same window's
    log-return volatility scaled to the window length.
    """
    close = clean_prices(close)
    if close.empty:
        return close.copy()
    log_ret = _log_returns(close)
    as_of = latest_as_of_date(pd.DatetimeIndex(close.index))
    frame, _, _ = calendar_period_metrics(
        close, log_ret, months, latest_as_of=as_of, anchor_limit=None
    )
    return frame


def latest_sharpe(close: pd.DataFrame, months: int) -> pd.Series:
    """Period-scale Sharpe on the latest observation date only.

    Same value as ``sharpe(close, months).iloc[-1]``, without walking every
    earlier date to get there.
    """
    return _latest_sharpe(clean_prices(close), months)


def _latest_sharpe(close: pd.DataFrame, months: int) -> pd.Series:
    """As :func:`latest_sharpe`, on an already-cleaned frame."""
    if close.empty:
        return pd.Series(dtype=float)
    log_ret = _log_returns(close)
    as_of = latest_as_of_date(pd.DatetimeIndex(close.index))
    frame, _, _ = calendar_period_metrics(
        close, log_ret, months, latest_as_of=as_of, anchor_limit=None, last_row_only=True
    )
    return frame.iloc[-1]


def _period_z_scores(
    close: pd.DataFrame, months: Sequence[int] = MOMENTUM_MONTHS
) -> dict[int, pd.DataFrame]:
    """Winsorised cross-sectional z-score of each horizon's Sharpe."""
    if close.empty:
        return {}
    log_ret = _log_returns(close)
    as_of = latest_as_of_date(pd.DatetimeIndex(close.index))
    scores: dict[int, pd.DataFrame] = {}
    for period in months:
        frame, _, _ = calendar_period_metrics(
            close, log_ret, period, latest_as_of=as_of, anchor_limit=None
        )
        scores[period] = winsorised_cross_section_z(frame)
    return scores


def momentum_score(
    prices: pd.DataFrame,
    months: Sequence[int] = MOMENTUM_MONTHS,
    weights: Sequence[float] = MOMENTUM_WEIGHTS,
) -> pd.DataFrame:
    """Weighted cross-sectional Z-score of calendar-period Sharpe.

    Each Sharpe component uses its own calendar horizon. If a stock does not
    yet have enough history for a longer horizon, that component is omitted
    and the remaining weights are renormalized for that stock, so newer stocks
    are not penalised solely for lacking 9M/12M history. The minimum-history
    eligibility rule still gates the screener.
    """
    prices = clean_prices(prices)
    if len(months) != len(weights):
        raise ValueError("months and weights must have equal length")
    if prices.empty:
        return prices.copy()

    valid_counts = prices.notna().sum()
    eligible = valid_counts >= MIN_HISTORY
    result = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    weight_available = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    z_scores = _period_z_scores(prices, months)
    for period, weight in zip(months, weights):
        z = z_scores.get(period)
        if z is None:
            continue
        result = result.add(z.fillna(0.0) * weight, fill_value=0)
        weight_available = weight_available.add(z.notna().astype(float) * weight, fill_value=0)

    # Renormalize the available component weights independently for each stock.
    # Stocks below MIN_HISTORY remain ineligible regardless of short-window data.
    result = result.div(weight_available.replace(0, np.nan))
    result.loc[:, ~eligible] = np.nan
    return result


def technical_snapshot(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """Build only technical metrics derivable from canonical Adj Close + Volume."""
    close, volume = map(clean_prices, (close, volume))
    latest = close.apply(_last_valid)
    out = pd.DataFrame(index=close.columns)
    history_counts = close.notna().sum()
    out["History Days"] = history_counts
    out["Eligible"] = history_counts >= MIN_HISTORY
    out["CMP"] = latest

    for span in (50, 100, 200):
        ema = close.ewm(span=span, min_periods=span).mean().apply(_last_valid)
        out[f"EMA {span}"] = ema
        out[f"Above EMA {span}"] = latest > ema
        out[f"% EMA {span}"] = (latest / ema - 1) * 100

    # 52 weeks is a calendar year, not the last 252 rows.
    high_52w = close.loc[_calendar_slice(close, 12):].max()
    out["52W High"] = high_52w
    out["% From 52W High"] = (latest / high_52w - 1) * 100
    out["Within 20% of 52W High"] = out["% From 52W High"] >= -20

    out = out.join(_returns(close))

    # Frog-in-the-pan persistence over the calendar 6M window.
    recent = _log_returns(close).loc[_calendar_slice(close, 6):]
    out["Persistence 6M %"] = recent.gt(0).sum() / recent.notna().sum().replace(0, np.nan) * 100
    vol_avg = volume.rolling(20, min_periods=20).mean().apply(_last_valid)
    out["Volume"] = volume.apply(_last_valid)
    out["Volume Ratio"] = out["Volume"] / vol_avg.replace(0, np.nan)
    return out


def _calendar_slice(frame: pd.DataFrame, months: int) -> pd.Timestamp:
    """First observation date of the trailing calendar window of `months`."""
    index = pd.DatetimeIndex(frame.index)
    if index.empty:
        return pd.NaT
    starts = calendar_start_positions(index, months, latest_as_of=latest_as_of_date(index))
    return pd.Timestamp(index[int(starts[-1])])


def industry_relative(scores: pd.Series, universe: pd.DataFrame) -> pd.Series:
    frame = universe.set_index("Symbol").reindex(scores.index)
    industries = frame["Industry"].fillna("Other")
    return scores - scores.groupby(industries).transform("mean")


def momentum_acceleration(prices: pd.DataFrame) -> pd.Series:
    """Short-vs-long risk-adjusted momentum acceleration across calendar horizons."""
    prices = clean_prices(prices)
    if prices.empty:
        return pd.Series(dtype=float)
    current = {period: _latest_sharpe(prices, period) for period in MOMENTUM_MONTHS}
    short = 0.10 * _series_z(current[1]) + 0.35 * _series_z(current[3]) + 0.55 * _series_z(current[6])
    long = 0.45 * _series_z(current[9]) + 0.55 * _series_z(current[12])
    return short - long


def _series_z(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    if len(valid) < 3 or valid.std() == 0:
        return pd.Series(0.0, index=series.index)
    return (series - valid.mean()) / valid.std()


def zscore(s: pd.Series, clip: float = 3.0) -> pd.Series:
    return _series_z(s).clip(-clip, clip)


CHART_EMA_SPANS = (20, 50, 100, 200)


def relative_strength(stock: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Relative strength of a stock vs the benchmark, indexed to 100 at the window start.

    Above 100 means the stock has outperformed the benchmark since the first
    common date in the window; below 100 means it has lagged. Indexing to the
    window start is what makes the line readable on any timeframe: it always
    answers "since this chart begins", not "since some fixed epoch".
    """
    aligned = pd.DataFrame({"stock": stock, "benchmark": benchmark}).dropna()
    if len(aligned) < 2:
        return pd.Series(dtype=float)
    ratio = aligned["stock"] / aligned["benchmark"].replace(0, np.nan)
    ratio = ratio.dropna()
    if ratio.empty:
        return pd.Series(dtype=float)
    return (ratio / ratio.iloc[0]) * 100.0


def chart_overlays(close: pd.Series, spans: Sequence[int] = CHART_EMA_SPANS) -> dict[int, pd.Series]:
    """EMA overlays for the price chart, computed on the full history.

    The EMAs are computed before the chart window is sliced. An EMA restarted at
    the left edge of a 3-month view is not the 200 EMA -- it is a 60-observation
    average wearing its name.
    """
    return {span: close.ewm(span=span, min_periods=span).mean() for span in spans}
