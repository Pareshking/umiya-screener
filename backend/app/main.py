from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from src.storage import ObjectStoreConfig, download_prefix, read_pointer
from .schemas import ScreenerQuery
from .service import FILTERABLE, MetricsCacheStale, MetricsCacheUnavailable, query, store

ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data_cache" / "price_history"
app = FastAPI(title="Umiya Screener API", version="0.4.1")
origins = [item.strip() for item in os.getenv("ALLOWED_ORIGINS", "https://pareshpatel.vercel.app").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])


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


@app.get("/api/v1/health")
def health() -> dict:
    try:
        store.get()
        ready, detail = True, None
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        ready, detail = False, str(exc)
    return {"status": "ok" if ready else "degraded", "dataset_ready": ready, "detail": detail, "built_at": store.built_at.isoformat() if store.built_at else None}


@app.get("/api/v1/screener/metadata")
def metadata() -> dict:
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
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
def stock_chart(symbol: str, days: int = Query(252, ge=20, le=2520)) -> dict:
    symbol = symbol.upper().replace(".NS", "")
    dataset, metadata = _ensure_price_dataset()
    try:
        close = pd.read_parquet(dataset / "adj_close.parquet", columns=[symbol])
        volume = pd.read_parquet(dataset / "volume.parquet", columns=[symbol])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Chart data unavailable for {symbol}.") from exc
    chart = pd.DataFrame({"date": close.index, "adj_close": close[symbol].values, "volume": volume[symbol].reindex(close.index).values}).dropna(subset=["adj_close"]).tail(days)
    return {"symbol": symbol, "market_as_of": metadata.get("market_as_of"), "data_contract": ["adj_close", "volume"], "rows": chart.where(pd.notna(chart), None).to_dict(orient="records")}
