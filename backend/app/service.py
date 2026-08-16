from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from src.config import METRICS_CACHE_PATH, METRICS_CACHE_TTL_HOURS
from src.data import fetch_ohlcv, load_universe
from src.quant import momentum_acceleration, momentum_score, technical_snapshot


class MetricsCacheUnavailable(RuntimeError):
    """Raised when the API has no prebuilt analytical dataset."""


class MetricsCacheStale(RuntimeError):
    """Raised when the analytical dataset is older than the configured TTL."""


def build_metric_frame() -> tuple[pd.DataFrame, datetime]:
    """Build the market-wide analytical dataset.

    This is an offline/data-pipeline operation. It is deliberately not called
    by normal API queries or page loads. Use scripts/build_metrics.py or a
    scheduled job to refresh the dataset.
    """
    universe = load_universe()
    data = fetch_ohlcv(universe["Symbol"].tolist(), period="2y")
    close, high, low, volume = (
        data["close"], data["high"], data["low"], data["volume"]
    )
    if close.empty:
        raise RuntimeError("No price data was returned for the NSE 750 universe.")

    scores = momentum_score(close).iloc[-1].rename("Momentum Score")
    accel = momentum_acceleration(close).rename("Acceleration")
    tech = technical_snapshot(close, high, low, volume)
    frame = universe.set_index("Symbol").join([scores, accel, tech], how="left")

    frame["Industry Relative"] = frame["Momentum Score"] - frame.groupby("Industry")["Momentum Score"].transform("mean")
    frame["Rank"] = frame["Momentum Score"].rank(
        ascending=False, method="min", na_option="bottom"
    ).astype("Int64")
    frame["R² 1Y"] = _rolling_r2(close, 252).iloc[-1].reindex(frame.index)
    frame["3M Sharpe"] = _sharpe(close, 63).iloc[-1].reindex(frame.index)
    frame["6M Sharpe"] = _sharpe(close, 126).iloc[-1].reindex(frame.index)
    frame = frame.reset_index()

    built_at = datetime.now(timezone.utc)
    return frame, built_at


def write_metric_cache(frame: pd.DataFrame, built_at: datetime) -> None:
    """Atomically publish a completed analytical dataset."""
    METRICS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = METRICS_CACHE_PATH.with_suffix(".tmp.parquet")
    frame.to_parquet(tmp, index=False)
    tmp.replace(METRICS_CACHE_PATH)


def _load_cache() -> tuple[pd.DataFrame, datetime] | None:
    if not METRICS_CACHE_PATH.exists():
        return None
    modified = datetime.fromtimestamp(METRICS_CACHE_PATH.stat().st_mtime, tz=timezone.utc)
    try:
        frame = pd.read_parquet(METRICS_CACHE_PATH)
    except (OSError, ValueError, ImportError):
        return None
    return frame, modified


def _rolling_r2(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    logp = np.log(prices.clip(lower=0.01))
    t = pd.Series(np.arange(len(logp), dtype=float), index=logp.index)
    return logp.rolling(window, min_periods=max(10, int(window * 0.8))).corr(t) ** 2


def _sharpe(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    ret = np.log(prices / prices.shift(1).replace(0, np.nan))
    change = np.log(prices / prices.shift(window).replace(0, np.nan))
    vol = ret.rolling(window, min_periods=max(10, int(window * 0.8))).std() * np.sqrt(window)
    return change / vol.replace(0, np.nan)


class ScreenerStore:
    """Read-only serving store for the precomputed analytical dataset.

    API requests never download market data and never rebuild the NSE 750
    metrics. Dataset construction belongs to the scheduled/offline pipeline.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: pd.DataFrame | None = None
        self._built_at: datetime | None = None

    def get(self) -> pd.DataFrame:
        if self._frame is not None:
            return self._frame.copy()
        with self._lock:
            if self._frame is not None:
                return self._frame.copy()
            cached = _load_cache()
            if cached is None:
                raise MetricsCacheUnavailable(
                    "Screener dataset is not built yet. Run scripts/build_metrics.py."
                )
            frame, built_at = cached
            if datetime.now(timezone.utc) - built_at > timedelta(hours=METRICS_CACHE_TTL_HOURS):
                raise MetricsCacheStale(
                    "Screener dataset is stale. Run scripts/build_metrics.py."
                )
            self._frame, self._built_at = frame, built_at
            return frame.copy()

    @property
    def built_at(self) -> datetime | None:
        return self._built_at


store = ScreenerStore()

FILTERABLE = [
    "Rank", "Index", "CMP", "Momentum Score", "Industry Relative", "Acceleration",
    "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe",
    "R² 1Y", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200", "ATR %",
    "Persistence 6M %", "Volume Ratio", "Industry", "Within 20% of 52W High",
]


def query(payload) -> dict:
    frame = store.get()
    for flt in payload.filters:
        field = flt.field
        if field not in frame.columns:
            continue
        s = frame[field]
        op, value = flt.operator, flt.value
        if op == "in":
            values = value if isinstance(value, list) else [value]
            frame = frame[s.isin(values)]
        elif op == "=":
            frame = frame[s == value]
        else:
            numeric = pd.to_numeric(s, errors="coerce")
            v = float(value)
            mask = {">": numeric > v, ">=": numeric >= v, "<": numeric < v, "<=": numeric <= v}[op]
            frame = frame[mask]

    field = payload.sort.field if payload.sort.field in frame.columns else "Rank"
    frame = frame.sort_values(field, ascending=payload.sort.direction == "asc", na_position="last")
    total = len(frame)
    start = (payload.page - 1) * payload.page_size
    page = frame.iloc[start:start + payload.page_size].copy()
    page = page.replace({np.nan: None})
    return {
        "total": total,
        "page": payload.page,
        "page_size": payload.page_size,
        "rows": page.to_dict(orient="records"),
        "available_filters": FILTERABLE,
        "built_at": store.built_at.isoformat() if store.built_at else None,
    }
