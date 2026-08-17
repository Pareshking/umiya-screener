from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .config import MIN_HISTORY

MOMENTUM_WINDOWS = (21, 63, 126, 189, 252)
MOMENTUM_WEIGHTS = (0.10, 0.30, 0.30, 0.20, 0.10)


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Normalize dates and forward-fill gaps after each stock's first observation.

    This preserves the common market-date grid used by the original V1
    pipeline while keeping V2's canonical Adjusted Close input. Values before
    a stock's first real observation are never imputed.
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
        out.loc[first:, column] = out.loc[first:, column].ffill()
    return out


def _last_valid(series: pd.Series) -> float:
    valid = series.dropna()
    return float(valid.iloc[-1]) if not valid.empty else np.nan


def eligible_symbols(prices: pd.DataFrame, min_history: int = MIN_HISTORY) -> pd.Index:
    if prices.empty:
        return pd.Index([], dtype=object)
    return prices.notna().sum(axis=0).loc[lambda s: s >= min_history].index


def _return_by_observations(close: pd.DataFrame, window: int) -> pd.Series:
    values: dict[str, float] = {}
    for symbol in close.columns:
        series = close[symbol].dropna()
        values[symbol] = np.nan if len(series) <= window else (series.iloc[-1] / series.iloc[-window - 1] - 1) * 100
    return pd.Series(values, index=close.columns, dtype=float)


def returns(close: pd.DataFrame, windows: Sequence[int] = MOMENTUM_WINDOWS) -> pd.DataFrame:
    close = clean_prices(close)
    out = pd.DataFrame(index=close.columns)
    labels = {21: "1M Return", 63: "3M Return", 126: "6M Return", 189: "9M Return", 252: "12M Return"}
    for window in windows:
        values = _return_by_observations(close, window)
        out[labels[window]] = values
    return out


def sharpe(close: pd.DataFrame, window: int) -> pd.DataFrame:
    """Cumulative log return divided by same-window daily-log-return SD, scaled by sqrt(window)."""
    close = clean_prices(close)
    logret = np.log(close / close.shift(1).replace(0, np.nan))
    cumulative = np.log(close / close.shift(window).replace(0, np.nan))
    raw_sd = logret.rolling(window, min_periods=window).std()
    return cumulative / raw_sd.replace(0, np.nan) / np.sqrt(window)


def _cross_sectional_z(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    std = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).div(std, axis=0).clip(-3, 3)


def momentum_score(
    prices: pd.DataFrame,
    windows: Sequence[int] = MOMENTUM_WINDOWS,
    weights: Sequence[float] = MOMENTUM_WEIGHTS,
) -> pd.DataFrame:
    """Weighted cross-sectional Z-score of pure Sharpe across available lookbacks.

    Each Sharpe component uses its own matching window. If a stock does not
    yet have enough history for a longer horizon, that component is omitted
    and the remaining weights are renormalized for that stock. This avoids
    penalizing newer stocks solely for lacking 9M/12M history while retaining
    the minimum-history eligibility rule for the screener.
    """
    prices = clean_prices(prices)
    if len(windows) != len(weights):
        raise ValueError("windows and weights must have equal length")

    valid_counts = prices.notna().sum()
    eligible = valid_counts >= MIN_HISTORY
    result = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    weight_available = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for window, weight in zip(windows, weights):
        risk = sharpe(prices, window)
        risk.loc[:, valid_counts < window + 1] = np.nan

        z = _cross_sectional_z(risk)
        available = z.notna().astype(float)
        result = result.add(z.fillna(0) * weight, fill_value=0)
        weight_available = weight_available.add(available * weight, fill_value=0)

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

    high_52w = close.tail(min(252, len(close))).max()
    out["52W High"] = high_52w
    out["% From 52W High"] = (latest / high_52w - 1) * 100
    out["Within 20% of 52W High"] = out["% From 52W High"] >= -20

    out = out.join(returns(close))

    logret = np.log(close / close.shift(1).replace(0, np.nan))
    recent = logret.tail(126)
    out["Persistence 6M %"] = recent.gt(0).sum() / recent.notna().sum().replace(0, np.nan) * 100
    vol_avg = volume.rolling(20, min_periods=20).mean().apply(_last_valid)
    out["Volume"] = volume.apply(_last_valid)
    out["Volume Ratio"] = out["Volume"] / vol_avg.replace(0, np.nan)
    return out


def industry_relative(scores: pd.Series, universe: pd.DataFrame) -> pd.Series:
    frame = universe.set_index("Symbol").reindex(scores.index)
    industries = frame["Industry"].fillna("Other")
    return scores - scores.groupby(industries).transform("mean")


def momentum_acceleration(prices: pd.DataFrame) -> pd.Series:
    """Short-vs-long risk-adjusted momentum acceleration."""
    prices = clean_prices(prices)
    current = {window: sharpe(prices, window).iloc[-1] for window in MOMENTUM_WINDOWS}
    short = 0.10 * _series_z(current[21]) + 0.35 * _series_z(current[63]) + 0.55 * _series_z(current[126])
    long = 0.45 * _series_z(current[189]) + 0.55 * _series_z(current[252])
    return short - long


def _series_z(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    if len(valid) < 3 or valid.std() == 0:
        return pd.Series(0.0, index=series.index)
    return (series - valid.mean()) / valid.std()


def zscore(s: pd.Series, clip: float = 3.0) -> pd.Series:
    return _series_z(s).clip(-clip, clip)
