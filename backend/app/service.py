from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import METRICS_CACHE_PATH, METRICS_CACHE_TTL_HOURS
from src.quant import (
    classify_setup,
    clean_holidays,
    industry_relative,
    momentum_acceleration,
    latest_sharpe,
    max_drawdown,
    momentum_score,
    rank_delta,
    score_percentile,
    sma_distance,
    technical_snapshot,
    universe_breadth,
)
from src.storage import ObjectStoreConfig, download_prefix, read_pointer

ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data_cache" / "price_history"
METRICS_ROOT = ROOT / "data_cache" / "metrics"


class MetricsCacheUnavailable(RuntimeError):
    pass


class MetricsCacheStale(RuntimeError):
    pass


def _load_phase1_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    pointer = PRICE_ROOT / "LATEST.json"
    if not pointer.exists():
        raise MetricsCacheUnavailable("Phase 1 price dataset is not published. Run the scheduled data refresh.")
    try:
        dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
        dataset = PRICE_ROOT / dataset_name
        if not dataset.is_dir():
            raise FileNotFoundError(dataset)
        close = pd.read_parquet(dataset / "adj_close.parquet")
        volume = pd.read_parquet(dataset / "volume.parquet")
        eligibility = pd.read_parquet(dataset / "eligibility.parquet")
        universe = pd.read_parquet(dataset / "universe.parquet")
        metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError, KeyError, json.JSONDecodeError) as exc:
        raise MetricsCacheUnavailable("Published Phase 1 dataset cannot be read.") from exc
    required_metadata = {"market_as_of", "built_at_utc", "schema_version"}
    if not required_metadata.issubset(metadata):
        raise MetricsCacheUnavailable("Published Phase 1 dataset metadata is incomplete.")
    return close, volume, eligibility, universe, metadata


def build_metric_frame() -> tuple[pd.DataFrame, datetime]:
    close, volume, eligibility, universe, metadata = _load_phase1_dataset()
    symbols = eligibility["Symbol"].astype(str).tolist()
    close, volume = close.reindex(columns=symbols), volume.reindex(columns=symbols)
    if close.empty or volume.empty or not symbols:
        raise RuntimeError("Canonical Phase 1 dataset contains no eligible stocks.")
    # Market holidays that leaked into the vendor date grid distort every
    # cross-sectional statistic computed on those dates.
    close = clean_holidays(close)
    volume = volume.reindex(index=close.index)
    # The engine already produces the whole score history, so where a stock has
    # come from over the last month and quarter costs nothing beyond reading
    # two more rows out of it.
    score_history = momentum_score(close)
    scores = score_history.iloc[-1].rename("Momentum Score")
    acceleration = momentum_acceleration(close).rename("Acceleration")
    technical = technical_snapshot(close, volume)
    frame = universe.set_index("Symbol").reindex(symbols).join([scores, acceleration, technical], how="left")
    frame = frame.join(
        eligibility.set_index("Symbol")[["Last Price Date", "Data Age Days", "Last Volume Date", "Volume Age Days"]],
        how="left",
    )
    frame["Industry Relative"] = industry_relative(frame["Momentum Score"], universe)
    frame["Rank"] = frame["Momentum Score"].rank(ascending=False, method="min", na_option="bottom").astype("Int64")
    frame["3M Sharpe"] = latest_sharpe(close, 3).reindex(frame.index)
    frame["6M Sharpe"] = latest_sharpe(close, 6).reindex(frame.index)
    frame["Score Percentile"] = score_percentile(frame["Momentum Score"])
    frame["Rank \u03941M"] = rank_delta(score_history, 1).reindex(frame.index)
    frame["Rank \u03943M"] = rank_delta(score_history, 3).reindex(frame.index)
    frame["Max DD 12M"] = max_drawdown(close, 12).reindex(frame.index)
    frame["% 200 DMA"] = sma_distance(close, 200).reindex(frame.index)
    # Setup depends on the columns above, so it is classified last.
    frame["Setup"] = classify_setup(frame)
    frame["Market As Of"] = pd.Timestamp(metadata["market_as_of"])
    frame["Dataset Schema"] = metadata.get("schema_version", "1.2")
    return frame.reset_index(), datetime.now(timezone.utc)


def write_metric_cache(frame: pd.DataFrame, built_at: datetime) -> None:
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
    tmp = METRICS_CACHE_PATH.with_suffix(".tmp.parquet")
    METRICS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(tmp, index=False)
    tmp.replace(METRICS_CACHE_PATH)


def _validate_metric_dataset(dataset: Path) -> bool:
    required = ("screener_metrics.parquet", "metadata.json")
    if not dataset.is_dir() or any(not (dataset / name).is_file() for name in required):
        return False
    try:
        metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
        if not metadata.get("built_at_utc") or metadata.get("source_contract") != ["adj_close", "volume"]:
            return False
        frame = pd.read_parquet(dataset / "screener_metrics.parquet")
        return not frame.empty and {"Symbol", "Momentum Score", "Market As Of"}.issubset(frame.columns)
    except (OSError, ValueError, ImportError, KeyError, json.JSONDecodeError):
        return False


def _sync_remote_metrics() -> bool:
    try:
        store = ObjectStoreConfig.from_env()
        prefix = read_pointer(store, "pointers/latest-metrics-dataset.json")
        dataset_name = prefix.rstrip("/").split("/")[-1]
        target = METRICS_ROOT / dataset_name
        if not _validate_metric_dataset(target):
            tmp = METRICS_ROOT / f".{dataset_name}.tmp"
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            download_prefix(store, prefix, tmp)
            if not _validate_metric_dataset(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
                return False
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            tmp.replace(target)
        pointer = METRICS_ROOT / "LATEST.json"
        pointer_tmp = METRICS_ROOT / "LATEST.tmp.json"
        pointer_tmp.write_text(json.dumps({"dataset": dataset_name}), encoding="utf-8")
        pointer_tmp.replace(pointer)
        return True
    except Exception:
        return False


def _load_cache() -> tuple[pd.DataFrame, datetime] | None:
    pointer = METRICS_ROOT / "LATEST.json"
    if pointer.exists():
        try:
            dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
            dataset = METRICS_ROOT / dataset_name
            if _validate_metric_dataset(dataset):
                metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
                built_at = datetime.fromisoformat(metadata["built_at_utc"])
                return pd.read_parquet(dataset / "screener_metrics.parquet"), built_at
        except (OSError, ValueError, ImportError, KeyError, json.JSONDecodeError):
            pass
    if _sync_remote_metrics():
        pointer = METRICS_ROOT / "LATEST.json"
        try:
            dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
            dataset = METRICS_ROOT / dataset_name
            metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
            return pd.read_parquet(dataset / "screener_metrics.parquet"), datetime.fromisoformat(metadata["built_at_utc"])
        except (OSError, ValueError, ImportError, KeyError, json.JSONDecodeError):
            pass
    if not METRICS_CACHE_PATH.exists():
        return None
    modified = datetime.fromtimestamp(METRICS_CACHE_PATH.stat().st_mtime, tz=timezone.utc)
    try:
        return pd.read_parquet(METRICS_CACHE_PATH), modified
    except (OSError, ValueError, ImportError):
        return None


class ScreenerStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: pd.DataFrame | None = None
        self._built_at: datetime | None = None

    def get(self) -> pd.DataFrame:
        if self._frame is not None and self._built_at is not None:
            if datetime.now(timezone.utc) - self._built_at <= timedelta(hours=METRICS_CACHE_TTL_HOURS):
                return self._frame.copy()
            with self._lock:
                self._frame = None
                self._built_at = None
        with self._lock:
            if self._frame is not None and self._built_at is not None:
                if datetime.now(timezone.utc) - self._built_at <= timedelta(hours=METRICS_CACHE_TTL_HOURS):
                    return self._frame.copy()
                self._frame = None
                self._built_at = None
            cached = _load_cache()
            if cached is None:
                raise MetricsCacheUnavailable("Screener dataset is not available. Configure R2 or run scripts/build_metrics.py.")
            frame, built_at = cached
            if datetime.now(timezone.utc) - built_at > timedelta(hours=METRICS_CACHE_TTL_HOURS):
                raise MetricsCacheStale("Screener dataset is stale. Wait for the scheduled data refresh.")
            self._frame, self._built_at = frame, built_at
            return frame.copy()

    @property
    def built_at(self) -> datetime | None:
        return self._built_at


store = ScreenerStore()

FILTERABLE = ["Rank", "Index", "Symbol", "CMP", "Momentum Score", "Score Percentile", "Setup", "Rank \u03941M", "Rank \u03943M", "Max DD 12M", "% 200 DMA", "Industry Relative", "Acceleration", "1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200", "Persistence 6M %", "Volume Ratio", "Industry", "Within 20% of 52W High", "Data Age Days"]
SORTABLE = ["Rank", "Symbol", "Company Name", "Industry", "Index", "CMP", "Momentum Score", "Score Percentile", "Setup", "Rank \u03941M", "Rank \u03943M", "Max DD 12M", "% 200 DMA", "Industry Relative", "Acceleration", "1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200", "Persistence 6M %", "Volume Ratio", "Data Age Days"]
_ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=", "in"}


def _apply_filter(frame: pd.DataFrame, field: str, op: str, value) -> pd.DataFrame:
    if field not in FILTERABLE or field not in frame.columns:
        raise ValueError(f"Unsupported filter field: {field}")
    if op not in _ALLOWED_OPERATORS:
        raise ValueError(f"Unsupported filter operator: {op}")
    s = frame[field]
    if op == "in":
        return frame[s.isin(value if isinstance(value, list) else [value])]
    if op == "=":
        if pd.api.types.is_numeric_dtype(s):
            try:
                return frame[pd.to_numeric(s, errors="coerce") == float(value)]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Filter value for {field} must be numeric for operator =") from exc
        return frame[s == value]
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Filter value for {field} must be numeric for operator {op}") from exc
    numeric = pd.to_numeric(s, errors="coerce")
    masks = {">": numeric > v, ">=": numeric >= v, "<": numeric < v, "<=": numeric <= v}
    return frame[masks[op]]


def query(payload) -> dict:
    frame = store.get()
    search = (payload.search or "").strip().casefold()
    if search:
        symbol = frame["Symbol"].astype(str).str.casefold()
        company = frame["Company Name"].astype(str).str.casefold()
        frame = frame[symbol.str.contains(search, regex=False, na=False) | company.str.contains(search, regex=False, na=False)]
    for flt in payload.filters:
        frame = _apply_filter(frame, flt.field, flt.operator, flt.value)
    field = payload.sort.field
    if field not in SORTABLE or field not in frame.columns:
        raise ValueError(f"Unsupported sort field: {field}")
    frame = frame.sort_values(field, ascending=payload.sort.direction == "asc", na_position="last", kind="stable")
    total = len(frame)
    pages = max(1, (total + payload.page_size - 1) // payload.page_size)
    effective_page = min(payload.page, pages)
    start = (effective_page - 1) * payload.page_size
    page = frame.iloc[start:start + payload.page_size].replace({np.nan: None})
    return {"total": total, "page": effective_page, "page_size": payload.page_size, "pages": pages, "rows": page.to_dict(orient="records"), "available_filters": FILTERABLE, "available_sorts": SORTABLE, "built_at": store.built_at.isoformat() if store.built_at else None}