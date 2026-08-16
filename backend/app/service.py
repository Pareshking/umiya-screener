from __future__ import annotations

import threading
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.data import fetch_ohlcv, load_universe
from src.quant import momentum_acceleration, momentum_score, technical_snapshot


class ScreenerStore:
    """In-process metric store. Expensive market-wide work happens once per refresh."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: pd.DataFrame | None = None
        self._built_at: datetime | None = None

    def get(self, force: bool = False) -> pd.DataFrame:
        if self._frame is not None and not force:
            return self._frame.copy()
        with self._lock:
            if self._frame is not None and not force:
                return self._frame.copy()
            universe = load_universe()
            # Keep the first 750 constituents deterministically when the source is larger.
            universe = universe.head(750).copy()
            data = fetch_ohlcv(universe["Symbol"].tolist(), period="2y")
            close, high, low, volume = data["close"], data["high"], data["low"], data["volume"]
            scores = momentum_score(close).iloc[-1].rename("Momentum Score")
            accel = momentum_acceleration(close).rename("Acceleration")
            tech = technical_snapshot(close, high, low, volume)
            frame = universe.set_index("Symbol").join([scores, accel, tech], how="left")
            frame["Industry Relative"] = frame["Momentum Score"] - frame.groupby("Industry")["Momentum Score"].transform("mean")
            # Rank is the stable default sort; NaNs naturally go to the bottom.
            frame["Rank"] = frame["Momentum Score"].rank(ascending=False, method="min", na_option="bottom").astype(int)
            frame["R² 1Y"] = self._rolling_r2(close, 252).iloc[-1].reindex(frame.index)
            frame["3M Sharpe"] = self._sharpe(close, 63).iloc[-1].reindex(frame.index)
            frame["6M Sharpe"] = self._sharpe(close, 126).iloc[-1].reindex(frame.index)
            frame = frame.reset_index()
            self._frame = frame
            self._built_at = datetime.now(timezone.utc)
            return frame.copy()

    @staticmethod
    def _rolling_r2(prices: pd.DataFrame, window: int) -> pd.DataFrame:
        logp = np.log(prices.clip(lower=0.01))
        t = pd.Series(np.arange(len(logp), dtype=float), index=logp.index)
        return logp.rolling(window, min_periods=max(10, int(window * .8))).corr(t) ** 2

    @staticmethod
    def _sharpe(prices: pd.DataFrame, window: int) -> pd.DataFrame:
        ret = np.log(prices / prices.shift(1).replace(0, np.nan))
        change = np.log(prices / prices.shift(window).replace(0, np.nan))
        vol = ret.rolling(window, min_periods=max(10, int(window * .8))).std() * np.sqrt(window)
        return change / vol.replace(0, np.nan)

    @property
    def built_at(self) -> datetime | None:
        return self._built_at


store = ScreenerStore()

FILTERABLE = [
    "Rank", "CMP", "Momentum Score", "Industry Relative", "Acceleration",
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
            frame = frame[s.isin(value)]
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
    return {"total": total, "page": payload.page, "page_size": payload.page_size, "rows": page.to_dict(orient="records"), "available_filters": FILTERABLE}
