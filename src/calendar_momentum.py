"""Calendar-period momentum primitives.

Ported from the reference implementation in Pareshking/Paresh, which the
1M/3M/6M/9M/12M horizons are actually defined against: **calendar periods,
not fixed trading-row windows**.

The screener previously read "1M" as "the last 21 rows" and "12M" as "the
last 252 rows". Those counts drift against the calendar — NSE trades a
variable number of sessions per month, and any holed session shifts every
window by a day — so a "12M return" could silently span 11 or 13 months
depending on how complete the vendor data happened to be.

Here, for each observation date the start target is that date minus the
requested number of calendar months, and the window opens on the first
available market date on or after that target.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

INDIA_TZ = ZoneInfo("Asia/Kolkata")

# How stale a window's opening price may be. Five sessions is one trading
# week: long enough to bridge the holes the price vendor leaves, short enough
# that a genuinely suspended stock still scores NaN instead of a stale number.
ANCHOR_STALENESS_LIMIT: int = 5

# A window is only real if its opening observation is close to the calendar
# target. Seven days absorbs weekends and exchange holidays; anything further
# means the dataset simply does not reach back that far, and the horizon stays
# NaN rather than quietly reporting a shorter period under a longer label.
WINDOW_START_TOLERANCE_DAYS: int = 7


def latest_as_of_date(index: pd.DatetimeIndex) -> pd.Timestamp:
    """Return a current India date for fresh data, else the last observation date."""
    idx = pd.DatetimeIndex(index)
    if idx.empty:
        raise ValueError("cannot derive an as-of date from an empty index")
    today = pd.Timestamp(datetime.now(INDIA_TZ).date())
    last_data_date = pd.Timestamp(idx[-1]).normalize()
    # Use today's calendar date for genuinely current data (including weekends
    # and short exchange holidays), but anchor historical/stale datasets to
    # their actual last observation so test and offline datasets cannot acquire
    # a multi-year synthetic lookback horizon.
    if today - last_data_date > pd.Timedelta(days=7):
        return last_data_date
    return max(today, last_data_date)


def calendar_start_positions(
    index: pd.DatetimeIndex,
    months: int,
    *,
    latest_as_of: pd.Timestamp | None = None,
) -> np.ndarray:
    """Return the first available observation on/after each calendar target date."""
    idx = pd.DatetimeIndex(index)
    if idx.empty:
        return np.array([], dtype=int)

    as_of = idx.normalize().to_series(index=np.arange(len(idx)))
    as_of.iloc[-1] = (
        pd.Timestamp(latest_as_of).normalize()
        if latest_as_of is not None
        else latest_as_of_date(idx)
    )
    targets = pd.DatetimeIndex(as_of.to_numpy()) - pd.DateOffset(months=months)
    return np.searchsorted(idx.values, targets.values, side="left")


def calendar_targets(
    index: pd.DatetimeIndex,
    months: int,
    *,
    latest_as_of: pd.Timestamp | None = None,
) -> pd.DatetimeIndex:
    """Calendar target start dates matching :func:`calendar_start_positions`."""
    idx = pd.DatetimeIndex(index)
    if idx.empty:
        return pd.DatetimeIndex([])
    as_of = idx.normalize().to_series(index=np.arange(len(idx)))
    as_of.iloc[-1] = (
        pd.Timestamp(latest_as_of).normalize()
        if latest_as_of is not None
        else latest_as_of_date(idx)
    )
    return pd.DatetimeIndex(as_of.to_numpy()) - pd.DateOffset(months=months)


def window_is_reachable(
    index: pd.DatetimeIndex,
    start: int,
    target: pd.Timestamp,
    end: int,
) -> bool:
    """True when the dataset actually reaches back to the calendar target."""
    if start >= end or start >= len(index):
        return False
    gap = pd.Timestamp(index[start]).normalize() - pd.Timestamp(target).normalize()
    return gap <= pd.Timedelta(days=WINDOW_START_TOLERANCE_DAYS)


def calendar_period_metrics(
    prices: pd.DataFrame,
    log_returns: pd.DataFrame,
    months: int,
    *,
    latest_as_of: pd.Timestamp | None = None,
    anchor_limit: int | None = ANCHOR_STALENESS_LIMIT,
    last_row_only: bool = False,
) -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    """Period-scale Sharpe over a calendar-defined rolling window.

    Returns ``(sharpe_frame, last_simple_return, start_positions)``. Only the
    economic horizon and the observation count are calendar-defined; the
    volatility math is the same period-scale Sharpe the screener always used
    (cumulative log return over the same window's log-return volatility).

    ``anchor_limit`` is how many sessions the window's opening price may be
    carried forward. Pass ``None`` when the caller has already bridged the
    gaps (``src.quant.clean_prices`` does): filling twice would stack the two
    limits and let a genuinely suspended stock anchor on a two-week-old price.

    ``last_row_only`` computes the Sharpe of the final observation date alone
    and leaves the earlier rows NaN. Callers that only read ``.iloc[-1]`` skip
    a per-date loop over the whole history that way.
    """
    prices = prices.sort_index()
    log_returns = log_returns.reindex(index=prices.index, columns=prices.columns)
    index = pd.DatetimeIndex(prices.index)
    n_rows, n_cols = prices.shape
    if n_rows == 0 or n_cols == 0:
        return (
            pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float),
            pd.Series(dtype=float, index=prices.columns),
            np.array([], dtype=int),
        )

    starts = calendar_start_positions(index, months, latest_as_of=latest_as_of)
    targets = calendar_targets(index, months, latest_as_of=latest_as_of)

    # The window's OPENING price is looked up on one exact session, and the
    # vendor holes sessions routinely. When the anchor lands on a holed session
    # the whole horizon goes NaN for that symbol even though it has a full
    # price history. So the anchor uses each symbol's last real close on or
    # before the start date, capped at ANCHOR_STALENESS_LIMIT sessions.
    # Nothing is synthesised: a suspended stock with no print for a week still
    # scores NaN, which is the honest answer.
    prices_anchor = prices if anchor_limit is None else prices.ffill(limit=anchor_limit)

    r = log_returns.to_numpy(dtype=float)
    valid_r = np.isfinite(r)
    cs_r = np.vstack([np.zeros((1, n_cols)), np.nancumsum(np.where(valid_r, r, 0.0), axis=0)])
    cs_r2 = np.vstack([np.zeros((1, n_cols)), np.nancumsum(np.where(valid_r, r * r, 0.0), axis=0)])
    cs_n = np.vstack([np.zeros((1, n_cols)), np.cumsum(valid_r.astype(float), axis=0)])

    sharpe = np.full((n_rows, n_cols), np.nan)
    # Pre-extract both frames to raw numpy before the loop: each .iloc[] call
    # dispatches through pandas bookkeeping (~2 us), plain numpy row indexing
    # costs ~20 ns.
    anchor_arr = prices_anchor.to_numpy(dtype=float)
    prices_arr = prices.to_numpy(dtype=float)

    rows = (n_rows - 1,) if last_row_only else range(n_rows)
    with np.errstate(invalid="ignore", divide="ignore"):
        for end in rows:
            start = int(starts[end])
            if not window_is_reachable(index, start, targets[end], end):
                continue

            p0 = anchor_arr[start]
            p1 = prices_arr[end]
            valid_price = np.isfinite(p0) & np.isfinite(p1) & (p0 != 0)

            rs = cs_r[end + 1] - cs_r[start + 1]
            rs2 = cs_r2[end + 1] - cs_r2[start + 1]
            rn = cs_n[end + 1] - cs_n[start + 1]
            mean_r = rs / np.where(rn > 0, rn, np.nan)
            population_var = (rs2 / np.where(rn > 0, rn, np.nan)) - (mean_r * mean_r)
            daily_sd = np.sqrt(np.maximum(population_var, 0.0))
            period_vol = daily_sd * np.sqrt(rn)

            log_return = np.full(n_cols, np.nan)
            log_return[valid_price] = np.log(
                np.maximum(p1[valid_price] / p0[valid_price], 0.001)
            )
            sharpe[end] = log_return / np.where(period_vol > 0, period_vol, np.nan)

    # Only the final row's simple return is kept: building a full returns
    # matrix and discarding every row but the last wastes megabytes per window.
    last_ret_arr = np.full(n_cols, np.nan)
    end_last = n_rows - 1
    start_last = int(starts[end_last])
    if window_is_reachable(index, start_last, targets[end_last], end_last):
        lp0 = anchor_arr[start_last]
        lp1 = prices_arr[end_last]
        lv = np.isfinite(lp0) & np.isfinite(lp1) & (lp0 != 0)
        last_ret_arr[lv] = lp1[lv] / lp0[lv] - 1.0

    sharpe_df = pd.DataFrame(sharpe, index=prices.index, columns=prices.columns)
    last_ret = pd.Series(last_ret_arr, index=prices.columns)
    return sharpe_df, last_ret, starts


def winsorised_cross_section_z(score: pd.DataFrame) -> pd.DataFrame:
    """Winsorise each date's cross-section at +/-3 sigma, then z-score it.

    One matrix pass rather than one pass per row. A row needs three real
    observations and non-zero spread to mean anything; below that it stays NaN.
    """
    array = score.to_numpy(dtype=float)
    valid = np.isfinite(array)
    counts = valid.sum(axis=1)

    # A date with no observations at all is normal (the warmup rows), and
    # nanmean/nanstd emit a RuntimeWarning per such row. Those rows are set to
    # NaN below, which is the intended answer, so the warning is noise.
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Mean of empty slice")
        warnings.filterwarnings("ignore", message="Degrees of freedom <= 0")
        mean = np.nanmean(array, axis=1, keepdims=True)
        sd = np.nanstd(array, axis=1, ddof=0, keepdims=True)
        clipped = np.clip(array, mean - 3.0 * sd, mean + 3.0 * sd)
        c_mean = np.nanmean(clipped, axis=1, keepdims=True)
        c_sd = np.nanstd(clipped, axis=1, ddof=0, keepdims=True)
        z = (clipped - c_mean) / (c_sd + 1e-12)

    # Guard on both the pre-clip and post-clip standard deviations: a guard on
    # sd alone misses the case where sd > 0 but winsorisation collapses c_sd.
    z[(counts < 3) | (sd.ravel() == 0.0) | (c_sd.ravel() == 0.0), :] = np.nan
    # Winsorisation shifts the post-clip mean/std, so z-scores can slightly
    # exceed +/-3 even after the input clip. Clamp the final result.
    return pd.DataFrame(z.clip(-3.0, 3.0), index=score.index, columns=score.columns)
