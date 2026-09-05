from __future__ import annotations

import csv
import io
import json
import os
import threading
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from src.storage import ObjectStoreConfig, download_prefix, read_pointer
from .operational import OperationalMiddleware
from .schemas import ScreenerQuery
from .service import FILTERABLE, MetricsCacheStale, MetricsCacheUnavailable, query, store

ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data_cache" / "price_history"
app = FastAPI(title="Umiya Screener API", version="0.4.1")
origins = [item.strip() for item in os.getenv("ALLOWED_ORIGINS", "https://pareshpatel.vercel.app").split(",") if item.strip()]
app.add_middleware(OperationalMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])

# Small per-process chart cache. The production dataset is immutable, so caching
# a requested symbol's price/volume series is safe until the published dataset changes.
_CHART_CACHE_DATASET: str | None = None
_CHART_CACHE: dict[str, pd.DataFrame] = {}
_CHART_CACHE_LOCK = threading.Lock()

# Serialises price-dataset hydration. The warm-up thread and a concurrent chart
# request would otherwise download into the same temporary directory and race on
# the rename.
_PRICE_DATASET_LOCK = threading.Lock()

# The published datasets change once per scheduled refresh, so a short shared
# cache is safe and saves a full origin round trip on every repeat view. The
# health/readiness probes stay uncached: their whole job is to report live state.
DATASET_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=3600"


def _cache_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _read_price_dataset(dataset: Path) -> tuple[Path, dict] | None:
    required = ("adj_close.parquet", "volume.parquet", "eligibility.parquet", "universe.parquet", "metadata.json")
    if not dataset.is_dir() or any(not (dataset / name).is_file() for name in required):
        return None
    try:
        metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
        if not metadata.get("market_as_of") or not metadata.get("data_contract"):
            return None
        return dataset, metadata
    except (OSError, KeyError, json.JSONDecodeError):
        return None


def _ensure_price_dataset() -> tuple[Path, dict]:
    with _PRICE_DATASET_LOCK:
        return _ensure_price_dataset_locked()


def _ensure_price_dataset_locked() -> tuple[Path, dict]:
    PRICE_ROOT.mkdir(parents=True, exist_ok=True)
    pointer = PRICE_ROOT / "LATEST.json"
    if pointer.exists():
        try:
            dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
            local = _read_price_dataset(PRICE_ROOT / dataset_name)
            if local is not None:
                return local
        except (OSError, KeyError, json.JSONDecodeError):
            pass

    try:
        remote = ObjectStoreConfig.from_env()
        prefix = read_pointer(remote, "pointers/latest-price-dataset.json")
        dataset_name = prefix.rstrip("/").split("/")[-1]
        target = PRICE_ROOT / dataset_name
        if _read_price_dataset(target) is None:
            tmp = PRICE_ROOT / f".{dataset_name}.tmp"
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            download_prefix(remote, prefix, tmp)
            if _read_price_dataset(tmp) is None:
                shutil.rmtree(tmp, ignore_errors=True)
                raise RuntimeError("Remote price dataset failed validation")
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            tmp.replace(target)
        pointer_tmp = PRICE_ROOT / "LATEST.tmp.json"
        pointer_tmp.write_text(json.dumps({"dataset": dataset_name}), encoding="utf-8")
        pointer_tmp.replace(pointer)
        local = _read_price_dataset(target)
        if local is None:
            raise RuntimeError("Published price dataset failed local validation")
        return local
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Price dataset is unavailable.") from exc


def _load_chart_frame(dataset: Path, symbol: str) -> pd.DataFrame:
    global _CHART_CACHE_DATASET
    dataset_key = str(dataset.resolve())
    with _CHART_CACHE_LOCK:
        if _CHART_CACHE_DATASET != dataset_key:
            _CHART_CACHE.clear()
            _CHART_CACHE_DATASET = dataset_key
        cached = _CHART_CACHE.get(symbol)
    if cached is not None:
        return cached
    try:
        close = pd.read_parquet(dataset / "adj_close.parquet", columns=[symbol])
        volume = pd.read_parquet(dataset / "volume.parquet", columns=[symbol])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Chart data unavailable for {symbol}.") from exc
    chart = pd.DataFrame({"date": close.index, "adj_close": close[symbol].values, "volume": volume[symbol].reindex(close.index).values}).dropna(subset=["adj_close"])
    with _CHART_CACHE_LOCK:
        if _CHART_CACHE_DATASET == dataset_key:
            _CHART_CACHE[symbol] = chart
    return chart


def _warm_price_dataset_now() -> None:
    # Failure is non-fatal; the chart endpoint retries lazily if the object store
    # is temporarily unavailable.
    try:
        _ensure_price_dataset()
    except Exception:
        pass


@app.on_event("startup")
def warm_price_dataset() -> None:
    """Hydrate the price dataset in the background, never blocking startup.

    This ran inline. A sync startup handler is awaited before uvicorn binds the
    port, so the ~37 MB price dataset was downloaded from R2 object-by-object
    before the process would accept a single connection -- and every cold start
    pays it again, because the container filesystem is ephemeral. The screener
    table needs none of it: it reads the ~0.3 MB metrics dataset. Only charts do.

    So the download moves to a daemon thread. The port binds immediately, the
    screener is servable as soon as the metrics dataset loads, and a chart
    arriving before the warm-up finishes simply waits on the same lock.
    """
    threading.Thread(target=_warm_price_dataset_now, name="warm-price-dataset", daemon=True).start()


@app.get("/api/v1/live")
def live() -> dict:
    """Liveness probe: process is running; no dataset dependency."""
    return {"status": "alive"}


@app.get("/api/v1/ready")
def ready() -> dict:
    """Readiness probe: API is ready only when a fresh metrics dataset is usable."""
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "reason": str(exc)}) from exc
    built_at = store.built_at.isoformat() if store.built_at else None
    market_as_of = str(frame["Market As Of"].iloc[0].date()) if not frame.empty else None
    return {"status": "ready", "dataset_ready": True, "rows": len(frame), "built_at": built_at, "market_as_of": market_as_of, "data_contract": ["adj_close", "volume"]}


@app.get("/api/v1/health")
def health() -> dict:
    try:
        store.get()
        ready_state, detail = True, None
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        ready_state, detail = False, str(exc)
    built_at = store.built_at.isoformat() if store.built_at else None
    return {"status": "ok" if ready_state else "degraded", "dataset_ready": ready_state, "detail": detail, "built_at": built_at, "max_metrics_age_hours": 24}


@app.get("/api/v1/screener/metadata")
def metadata(response: Response) -> dict:
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    response.headers["Cache-Control"] = DATASET_CACHE_CONTROL
    return {"universe": len(frame), "universe_name": "NIFTY 750", "source_counts": {str(k): int(v) for k, v in frame["Index"].value_counts().to_dict().items()}, "industries": sorted(frame["Industry"].dropna().astype(str).unique().tolist()), "filters": FILTERABLE, "built_at": store.built_at.isoformat() if store.built_at else None, "market_as_of": str(frame["Market As Of"].iloc[0].date()) if not frame.empty else None, "data_contract": ["adj_close", "volume"]}


@app.post("/api/v1/screener/query")
def screener(payload: ScreenerQuery) -> dict:
    try:
        return query(payload)
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Screener query failed") from exc


@app.post("/api/v1/screener/export")
def screener_export(payload: ScreenerQuery) -> Response:
    try:
        first = query(payload.model_copy(update={"page": 1, "page_size": 200}))
        rows = list(first.get("rows", []))
        for page in range(2, int(first.get("pages", 1)) + 1):
            rows.extend(query(payload.model_copy(update={"page": page, "page_size": 200})).get("rows", []))
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Screener export failed") from exc
    output = io.StringIO(newline="")
    if rows:
        fields = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("No matching stocks\n")
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=umiya-screener.csv"})


@app.get("/api/v1/stocks/{symbol}")
def stock(symbol: str, response: Response) -> dict:
    symbol = symbol.upper().replace(".NS", "")
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    rows = frame[frame["Symbol"] == symbol]
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} is not in the current eligible universe.")
    response.headers["Cache-Control"] = DATASET_CACHE_CONTROL
    return rows.iloc[0].replace({pd.NA: None}).to_dict()


@app.get("/api/v1/stocks/{symbol}/chart")
def stock_chart(response: Response, symbol: str, days: int = Query(252, ge=20, le=2520)) -> dict:
    symbol = symbol.upper().replace(".NS", "")
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    if frame[frame["Symbol"] == symbol].empty:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} is not in the current eligible universe.")
    dataset, metadata = _ensure_price_dataset()
    chart = _load_chart_frame(dataset, symbol).tail(days)
    if chart.empty:
        raise HTTPException(status_code=404, detail=f"Chart data unavailable for {symbol}.")
    response.headers["Cache-Control"] = DATASET_CACHE_CONTROL
    return {"symbol": symbol, "market_as_of": metadata.get("market_as_of"), "data_contract": ["adj_close", "volume"], "rows": chart.where(pd.notna(chart), None).to_dict(orient="records")}
