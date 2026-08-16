from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .config import MIN_HISTORY


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Preserve the trading-date index and tolerate per-stock missing values.

    Missing exchange-wide dates are normally absent from the source entirely
    (weekends/holidays), so they must not be manufactured or treated as a
    failed data build. Likewise, a partial source gap for one stock must not
    delete the trading date for every other stock.

    We intentionally do not forward-fill prices here. Forward-filling can turn
    a genuine stale-price/suspension gap into a false zero return and can
    contaminate momentum, volatility and R². Individual metrics decide how
    many valid observations they require.
    """
    if prices.empty:
        return prices.copy()
    cleaned = prices.copy()
    cleaned.index = pd.to_datetime(cleaned.index)
    return cleaned.sort_index()


def eligible_symbols(prices: pd.DataFrame, min_history: int = MIN_HISTORY) -> pd.Index:
    """Return symbols with at least ``min_history`` valid price observations."""
    if prices.empty:
        return pd.Index([], dtype=object)
    return prices.notna().sum(axis=0).loc[lambda s: s >= min_history].index


def _last_valid(series: pd.Series) -> float:
    valid = series.dropna()
    return float(valid.iloc[-1]) if not valid.empty else np.nan


def _return_by_observations(close: pd.DataFrame, window: int) -> pd.Series:
    """Return using the last valid observation and ``window`` valid observations back."""
    values = {}
    for symbol in close.columns:
        series = close[symbol].dropna()
        if len(series) <= window:
            values[symbol] = np.nan
        else:
            values[symbol] = (series.iloc[-1] / series.iloc[-window - 1] - 1) * 100
    return pd.Series(values, index=close.columns, dtype=float)


def zscore(s: pd.Series, clip: float = 3.0) -> pd.Series:
    valid = s.dropna()
    if len(valid) < 3 or valid.std() == 0:
        return pd.Series(0.0, index=s.index)
    mean, std = valid.mean(), valid.std()
    return ((s.clip(mean - clip * std, mean + clip * std) - mean) / (std + 1e-12)).reindex(s.index)


def rolling_r2(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    logp = np.log(prices.clip(lower=0.01))
    t = pd.Series(np.arange(len(logp), dtype=float), index=logp.index)
    return logp.rolling(window, min_periods=max(int(window * 0.8), 10)).corr(t) ** 2


def sharpe_r2(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    logret = np.log(prices / prices.shift(1).replace(0, np.nan))
    change = np.log(prices / prices.shift(window).replace(0, np.nan))
    vol = logret.rolling(window, min_periods=max(int(window * 0.8), 10)).std() * np.sqrt(window)
    return (change / vol.replace(0, np.nan)) * rolling_r2(prices, window)


def momentum_score(prices: pd.DataFrame, windows: Sequence[int] = (21, 63, 126, 189, 252), weights: Sequence[float] = (0.10, 0.30, 0.30, 0.20, 0.10)) -> pd.DataFrame:
    """Cross-sectional weighted Z(Sharpe × R²) momentum score.

    Stocks with at least 126 observations remain eligible. A longer lookback
    may be unavailable; its contribution is zero rather than disqualifying
    the stock from the screener.
    """
    prices = clean_prices(prices)
    total = float(sum(weights)) or 1.0
    result = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    valid_counts = prices.notna().sum()
    eligible = valid_counts >= MIN_HISTORY
    for window, weight in zip(windows, weights):
        raw = sharpe_r2(prices, window)
        raw.loc[:, valid_counts < window] = np.nan
        mean = raw.mean(axis=1)
        std = raw.std(axis=1).replace(0, np.nan)
        z = raw.sub(mean, axis=0).div(std, axis=0).clip(-3, 3)
        result = result.add(z.fillna(0) * (weight / total))
    result.loc[:, ~eligible] = np.nan
    return result


def technical_snapshot(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """Build the core stock-level technical columns used by the screener."""
    close, high, low, volume = map(clean_prices, (close, high, low, volume))
    latest = close.apply(_last_valid)
    out = pd.DataFrame(index=close.columns)
    history_counts = close.notna().sum()
    out["History Days"] = history_counts
    out["Eligible"] = history_counts >= MIN_HISTORY
    out["CMP"] = latest
    for span in (50, 100, 200):
        ema = close.ewm(span=span, min_periods=max(20, span // 2)).mean().apply(_last_valid)
        out[f"EMA {span}"] = ema
        out[f"Above EMA {span}"] = latest > ema
        out[f"% EMA {span}"] = (latest / ema - 1) * 100

    high_52w = high.tail(min(252, len(high))).max()
    out["52W High"] = high_52w
    out["% From 52W High"] = (latest / high_52w - 1) * 100
    out["Within 20% of 52W High"] = out["% From 52W High"] >= -20

    for window, label in ((21, "1M"), (63, "3M"), (126, "6M"), (189, "9M"), (252, "12M")):
        values = _return_by_observations(close, window)
        if label == "12M":
            values = values.fillna(0.0)
        out[f"{label} Return"] = values

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()]).groupby(level=0).max()
    atr = tr.rolling(14, min_periods=5).mean().apply(_last_valid)
    out["ATR"] = atr
    out["ATR %"] = atr / latest * 100
    out["ATR Stop 2x"] = (latest - 2 * atr).clip(lower=0)
    out["Chandelier Exit"] = (high.tail(22).max() - 3 * atr).clip(lower=0)

    logret = np.log(close / close.shift(1))
    recent_logret = logret.tail(126)
    out["Persistence 6M %"] = recent_logret.gt(0).sum() / recent_logret.notna().sum() * 100
    vol_avg = volume.rolling(20, min_periods=10).mean().apply(_last_valid)
    latest_volume = volume.apply(_last_valid)
    out["Volume Ratio"] = latest_volume / vol_avg.replace(0, np.nan)
    return out


def industry_relative(scores: pd.Series, universe: pd.DataFrame) -> pd.Series:
    frame = universe.set_index("Symbol").reindex(scores.index)
    industries = frame["Industry"].fillna("Other")
    peer_mean = scores.groupby(industries).transform("mean")
    return scores - peer_mean


def momentum_acceleration(prices: pd.DataFrame) -> pd.Series:
    periods = {w: sharpe_r2(prices, w).iloc[-1] for w in (21, 63, 126, 189, 252)}
    short = 0.10 * zscore(periods[21]) + 0.35 * zscore(periods[63]) + 0.55 * zscore(periods[126])
    long = 0.45 * zscore(periods[189]) + 0.55 * zscore(periods[252])
    return short - long
