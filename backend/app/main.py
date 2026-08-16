from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ScreenerQuery
from .service import FILTERABLE, MetricsCacheStale, MetricsCacheUnavailable, query, store

ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data_cache" / "price_history"

app = FastAPI(title="Umiya Screener API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _cache_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _phase1_paths() -> tuple[Path, dict]:
    pointer = PRICE_ROOT / "LATEST.json"
    if not pointer.exists():
        raise HTTPException(status_code=503, detail="Price dataset is unavailable.")
    try:
        dataset_name = json.loads(pointer.read_text(encoding="utf-8"))["dataset"]
        dataset = PRICE_ROOT / dataset_name
        metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Price dataset metadata is unavailable.") from exc
    if not dataset.is_dir():
        raise HTTPException(status_code=503, detail="Published price dataset is missing.")
    return dataset, metadata


@app.get("/api/v1/health")
def health() -> dict:
    try:
        store.get()
        ready = True
        detail = None
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        ready = False
        detail = str(exc)
    return {"status": "ok" if ready else "degraded", "dataset_ready": ready, "detail": detail, "built_at": store.built_at.isoformat() if store.built_at else None}


@app.get("/api/v1/screener/metadata")
def metadata() -> dict:
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    return {
        "universe": len(frame),
        "universe_name": "NIFTY 750",
        "source_counts": {str(k): int(v) for k, v in frame["Index"].value_counts().to_dict().items()},
        "industries": sorted(frame["Industry"].dropna().astype(str).unique().tolist()),
        "filters": FILTERABLE,
        "built_at": store.built_at.isoformat() if store.built_at else None,
        "market_as_of": str(frame["Market As Of"].iloc[0].date()) if not frame.empty else None,
        "data_contract": ["adj_close", "volume"],
    }


@app.post("/api/v1/screener/query")
def screener(payload: ScreenerQuery) -> dict:
    try:
        return query(payload)
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Screener query failed") from exc


@app.get("/api/v1/stocks/{symbol}")
def stock(symbol: str) -> dict:
    symbol = symbol.upper().replace(".NS", "")
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    rows = frame[frame["Symbol"] == symbol]
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} is not in the current eligible universe.")
    return rows.iloc[0].replace({pd.NA: None}).to_dict()


@app.get("/api/v1/stocks/{symbol}/chart")
def stock_chart(symbol: str, days: int = 252) -> dict:
    symbol = symbol.upper().replace(".NS", "")
    days = max(20, min(days, 2520))
    dataset, metadata = _phase1_paths()
    try:
        close = pd.read_parquet(dataset / "adj_close.parquet", columns=[symbol])
        volume = pd.read_parquet(dataset / "volume.parquet", columns=[symbol])
    except (OSError, ValueError, ImportError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=f"Chart data unavailable for {symbol}.") from exc
    chart = pd.DataFrame({"date": close.index, "adj_close": close[symbol].values, "volume": volume[symbol].reindex(close.index).values}).dropna(subset=["adj_close"]).tail(days)
    return {"symbol": symbol, "market_as_of": metadata.get("market_as_of"), "data_contract": ["adj_close", "volume"], "rows": chart.where(pd.notna(chart), None).to_dict(orient="records")}
