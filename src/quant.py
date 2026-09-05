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


# ── Rank dynamics ───────────────────────────────────────────────────────────
# The composite score is a level; where a stock is *heading* is a different
# signal, and the engine already computes the full score history, so the
# rank it held a month or a quarter ago costs nothing extra to read off.

def cross_sectional_rank(scores: pd.Series) -> pd.Series:
    """Dense competition rank of a score cross-section, best = 1."""
    return scores.rank(ascending=False, method="min", na_option="keep")


def rank_as_of(score_history: pd.DataFrame, months: int) -> pd.Series:
    """Cross-sectional rank as it stood `months` calendar months ago.

    Uses the same calendar anchoring as every other horizon, so "rank a month
    ago" means the rank on the first session on or after that calendar date,
    not the rank 21 rows back.
    """
    if score_history.empty:
        return pd.Series(dtype=float)
    index = pd.DatetimeIndex(score_history.index)
    as_of = latest_as_of_date(index)
    starts = calendar_start_positions(index, months, latest_as_of=as_of)
    targets = calendar_targets(index, months, latest_as_of=as_of)
    end = len(index) - 1
    start = int(starts[end])
    if not window_is_reachable(index, start, targets[end], end):
        return pd.Series(np.nan, index=score_history.columns)
    return cross_sectional_rank(score_history.iloc[start])


def rank_delta(score_history: pd.DataFrame, months: int) -> pd.Series:
    """Places gained since `months` ago. Positive = moved up the table.

    Signed so that up is good, matching every other coloured column: a stock
    going from rank 40 to rank 12 reads +28, not -28.
    """
    past = rank_as_of(score_history, months)
    if past.empty or past.isna().all():
        return pd.Series(np.nan, index=score_history.columns)
    return past - cross_sectional_rank(score_history.iloc[-1])


def score_percentile(scores: pd.Series) -> pd.Series:
    """Percentile of each score within the eligible cross-section (0-99)."""
    return (scores.rank(pct=True, na_option="keep") * 100).clip(upper=99).round(0)


def max_drawdown(close: pd.DataFrame, months: int = 12) -> pd.Series:
    """Worst peak-to-trough decline over the trailing calendar window, in percent.

    Reported as a negative number, because that is the direction it describes.
    """
    close = clean_prices(close)
    if close.empty:
        return pd.Series(dtype=float)
    window = close.loc[_calendar_slice(close, months):]
    running_peak = window.cummax()
    drawdown = (window / running_peak.replace(0, np.nan) - 1) * 100
    return drawdown.min()


def sma_distance(close: pd.DataFrame, window: int = 200) -> pd.Series:
    """Percent distance of the latest close from its simple moving average.

    The 200 DMA is a different line from the 200 EMA and traders read them
    differently, so it is reported separately rather than aliased.
    """
    close = clean_prices(close)
    if close.empty:
        return pd.Series(dtype=float)
    sma = close.rolling(window, min_periods=window).mean().apply(_last_valid)
    latest = close.apply(_last_valid)
    return (latest / sma.replace(0, np.nan) - 1) * 100


# ── Setup classification ────────────────────────────────────────────────────
# A single word for what a row is doing, so the table can be skimmed without
# reading eight numbers per line. Every label is a stated rule over columns
# that already exist -- nothing here is a judgement the data cannot support,
# and the order below is the precedence order.

SETUP_RULES = (
    ("LEADER", "top decile score, above the 200 EMA, within 5% of its 52-week high"),
    ("BREAKOUT", "within 2% of its 52-week high on above-average volume"),
    ("STRONG", "top quartile score, above both the 50 and 200 EMA"),
    ("PULLBACK", "top quartile score but trading back below its 50 EMA"),
    ("RISING", "gained 20 or more places over the last three months"),
    ("BASING", "above the 200 EMA but more than 20% below its 52-week high"),
    ("WATCH", "everything else that is still above its 200 EMA"),
    ("WEAK", "below the 200 EMA"),
)


def classify_setup(frame: pd.DataFrame) -> pd.Series:
    """Label each row with the first matching rule in SETUP_RULES."""
    pct = frame.get("Score Percentile")
    from_high = frame.get("% From 52W High")
    ema50 = frame.get("% EMA 50")
    ema200 = frame.get("% EMA 200")
    vol = frame.get("Volume Ratio")
    d3m = frame.get("Rank Δ3M")

    empty = pd.Series(np.nan, index=frame.index)
    pct = empty if pct is None else pct
    from_high = empty if from_high is None else from_high
    ema50 = empty if ema50 is None else ema50
    ema200 = empty if ema200 is None else ema200
    vol = empty if vol is None else vol
    d3m = empty if d3m is None else d3m

    above200 = ema200 > 0
    above50 = ema50 > 0

    out = pd.Series("WEAK", index=frame.index, dtype=object)
    out[above200] = "WATCH"
    out[above200 & (from_high < -20)] = "BASING"
    out[above200 & (d3m >= 20)] = "RISING"
    out[(pct >= 75) & ~above50 & above200] = "PULLBACK"
    out[(pct >= 75) & above50 & above200] = "STRONG"
    out[(from_high >= -2) & (vol > 1.2)] = "BREAKOUT"
    out[(pct >= 90) & above200 & (from_high >= -5)] = "LEADER"
    out[ema200.isna()] = "—"
    return out


def universe_breadth(frame: pd.DataFrame) -> dict:
    """Participation statistics for the whole eligible universe.

    Breadth is a property of the market, not of whatever the current filters
    happen to return, so this is always computed over the full frame.
    """
    total = int(len(frame))
    if not total:
        return {"total": 0}

    def share(column: str, predicate) -> dict | None:
        # Guarded on column presence: a metrics dataset published before a
        # column existed is still perfectly servable, and this feeds the
        # endpoint the homepage calls first.
        if column not in frame.columns:
            return None
        count = int(predicate(pd.to_numeric(frame[column], errors="coerce")).sum())
        return {"count": count, "pct": round(count / total * 100, 1)}

    d1m = frame.get("Rank Δ1M")
    entered = exited = None
    if d1m is not None and "Rank" in frame.columns:
        rank_now = pd.to_numeric(frame["Rank"], errors="coerce")
        # rank_delta is signed so that up is good (past - now), so the rank a
        # month ago is today's rank PLUS the delta, not minus it.
        rank_past = rank_now + pd.to_numeric(d1m, errors="coerce")
        entered = int(((rank_now <= 50) & (rank_past > 50)).sum())
        exited = int(((rank_now > 50) & (rank_past <= 50)).sum())

    return {
        "total": total,
        "above_50_ema": share("% EMA 50", lambda c: c > 0),
        "above_200_ema": share("% EMA 200", lambda c: c > 0),
        "near_52w_high": share("% From 52W High", lambda c: c >= -10),
        "positive_3m": share("3M Return", lambda c: c > 0),
        "entered_top_50": entered,
        "exited_top_50": exited,
    }
