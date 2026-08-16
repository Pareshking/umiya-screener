from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import METRICS_CACHE_PATH, METRICS_CACHE_TTL_HOURS
from src.quant import industry_relative, momentum_acceleration, momentum_score, rolling_r2, sharpe, technical_snapshot

ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data_cache" / "price_history"
METRICS_ROOT = ROOT / "data_cache" / "metrics"


class MetricsCacheUnavailable(RuntimeError):
    """Raised when the API has no prebuilt analytical dataset."""


class MetricsCacheStale(RuntimeError):
    """Raised when the analytical dataset is older than the configured TTL."""


def _load_phase1_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    pointer = PRICE_ROOT / "LATEST.json"
    if not pointer.exists():
        raise MetricsCacheUnavailable("Phase 1 price dataset is not published. Run scripts/build_data.py.")
    try:
        dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise MetricsCacheUnavailable("LATEST.json is invalid.") from exc
    dataset = PRICE_ROOT / dataset_name
    if not dataset.is_dir():
        raise MetricsCacheUnavailable(f"Published dataset {dataset_name!r} is missing.")
    try:
        close = pd.read_parquet(dataset / "adj_close.parquet")
        volume = pd.read_parquet(dataset / "volume.parquet")
        eligibility = pd.read_parquet(dataset / "eligibility.parquet")
        universe = pd.read_parquet(dataset / "universe.parquet")
        metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError, json.JSONDecodeError) as exc:
        raise MetricsCacheUnavailable("Published Phase 1 dataset cannot be read.") from exc
    return close, volume, eligibility, universe, metadata


def build_metric_frame() -> tuple[pd.DataFrame, datetime]:
    close, volume, eligibility, universe, metadata = _load_phase1_dataset()
    symbols = eligibility["Symbol"].astype(str).tolist()
    close, volume = close.reindex(columns=symbols), volume.reindex(columns=symbols)
    if close.empty or volume.empty or not symbols:
        raise RuntimeError("Canonical Phase 1 dataset contains no eligible stocks.")

    scores = momentum_score(close).iloc[-1].rename("Momentum Score")
    acceleration = momentum_acceleration(close).rename("Acceleration")
    technical = technical_snapshot(close, volume)
    frame = universe.set_index("Symbol").reindex(symbols).join([scores, acceleration, technical], how="left")
    frame = frame.join(eligibility.set_index("Symbol")[["Last Price Date", "Data Age Days"]], how="left")
    frame["Industry Relative"] = industry_relative(frame["Momentum Score"], universe)
    frame["Rank"] = frame["Momentum Score"].rank(ascending=False, method="min", na_option="bottom").astype("Int64")
    frame["R² 1Y"] = rolling_r2(close, 252).iloc[-1].reindex(frame.index)
    frame["3M Sharpe"] = sharpe(close, 63).iloc[-1].reindex(frame.index)
    frame["6M Sharpe"] = sharpe(close, 126).iloc[-1].reindex(frame.index)
    frame["Market As Of"] = pd.Timestamp(metadata["market_as_of"])
    frame["Dataset Schema"] = metadata.get("schema_version", "1.1")
    return frame.reset_index(), datetime.now(timezone.utc)


def write_metric_cache(frame: pd.DataFrame, built_at: datetime) -> None:
    """Publish immutable local metric version then atomically advance pointer."""
    METRICS_ROOT.mkdir(parents=True, exist_ok=True)
    version = built_at.strftime("%Y%m%dT%H%M%SZ")
    target = METRICS_ROOT / f"dataset_{version}"
    candidate = METRICS_ROOT / f"dataset_{version}.tmp"
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        frame.to_parquet(candidate / "screener_metrics.parquet", index=False)
        metadata = {
            "schema_version": "2.0",
            "built_at_utc": built_at.isoformat(),
            "rows": int(len(frame)),
            "market_as_of": str(frame["Market As Of"].iloc[0].date()) if not frame.empty else None,
            "source_contract": ["adj_close", "volume"],
        }
        (candidate / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        candidate.replace(target)
    except Exception:
        import shutil
        shutil.rmtree(candidate, ignore_errors=True)
        raise

    pointer_tmp = METRICS_ROOT / "LATEST.tmp.json"
    pointer_tmp.write_text(json.dumps({"dataset": target.name}, indent=2), encoding="utf-8")
    pointer_tmp.replace(METRICS_ROOT / "LATEST.json")

    # Compatibility path for existing local deployments; it is not the source
    # of truth and can be deleted/rebuilt at any time.
    tmp = METRICS_CACHE_PATH.with_suffix(".tmp.parquet")
    METRICS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(tmp, index=False)
    tmp.replace(METRICS_CACHE_PATH)


def _load_cache() -> tuple[pd.DataFrame, datetime] | None:
    pointer = METRICS_ROOT / "LATEST.json"
    if pointer.exists():
        try:
            dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
            path = METRICS_ROOT / dataset_name / "screener_metrics.parquet"
            built_at = datetime.fromisoformat(json.loads((METRICS_ROOT / dataset_name / "metadata.json").read_text(encoding="utf-8"))["built_at_utc"])
            return pd.read_parquet(path), built_at
        except (OSError, ValueError, ImportError, KeyError, json.JSONDecodeError):
            return None
    if not METRICS_CACHE_PATH.exists():
        return None
    modified = datetime.fromtimestamp(METRICS_CACHE_PATH.stat().st_mtime, tz=timezone.utc)
    try:
        return pd.read_parquet(METRICS_CACHE_PATH), modified
    except (OSError, ValueError, ImportError):
        return None


class ScreenerStore:
    """Read-only serving store for the precomputed analytical dataset."""

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
                raise MetricsCacheUnavailable("Screener dataset is not built yet. Run scripts/build_metrics.py.")
            frame, built_at = cached
            if datetime.now(timezone.utc) - built_at > timedelta(hours=METRICS_CACHE_TTL_HOURS):
                raise MetricsCacheStale("Screener dataset is stale. Run scripts/build_metrics.py.")
            self._frame, self._built_at = frame, built_at
            return frame.copy()

    @property
    def built_at(self) -> datetime | None:
        return self._built_at


store = ScreenerStore()

FILTERABLE = [
    "Rank", "Index", "Symbol", "CMP", "Momentum Score", "Industry Relative", "Acceleration",
    "1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe",
    "R² 1Y", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200", "Persistence 6M %",
    "Volume Ratio", "Industry", "Within 20% of 52W High", "Data Age Days",
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
            masks = {">": numeric > v, ">=": numeric >= v, "<": numeric < v, "<=": numeric <= v}
            frame = frame[masks[op]]
    field = payload.sort.field if payload.sort.field in frame.columns else "Rank"
    frame = frame.sort_values(field, ascending=payload.sort.direction == "asc", na_position="last")
    total = len(frame)
    start = (payload.page - 1) * payload.page_size
    page = frame.iloc[start:start + payload.page_size].copy()
    page = page.replace({np.nan: None})
    return {"total": total, "page": payload.page, "page_size": payload.page_size, "rows": page.to_dict(orient="records"), "available_filters": FILTERABLE, "built_at": store.built_at.isoformat() if store.built_at else None}
