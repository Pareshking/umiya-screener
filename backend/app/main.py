from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ScreenerQuery
from .service import (
    FILTERABLE,
    MetricsCacheStale,
    MetricsCacheUnavailable,
    query,
    store,
)

app = FastAPI(title="Umiya Screener API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _cache_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@app.get("/api/v1/health")
def health() -> dict:
    try:
        store.get()
        ready = True
        detail = None
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        ready = False
        detail = str(exc)
    return {
        "status": "ok" if ready else "degraded",
        "dataset_ready": ready,
        "detail": detail,
        "built_at": store.built_at.isoformat() if store.built_at else None,
    }


@app.get("/api/v1/screener/metadata")
def metadata() -> dict:
    try:
        frame = store.get()
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc

    source_counts = {
        str(index): int(count)
        for index, count in frame["Index"].value_counts().to_dict().items()
    }
    return {
        "universe": len(frame),
        "universe_name": "NIFTY 750",
        "source_counts": source_counts,
        "industries": sorted(frame["Industry"].dropna().astype(str).unique().tolist()),
        "filters": FILTERABLE,
        "built_at": store.built_at.isoformat() if store.built_at else None,
    }


@app.post("/api/v1/screener/query")
def screener(payload: ScreenerQuery) -> dict:
    try:
        return query(payload)
    except (MetricsCacheUnavailable, MetricsCacheStale) as exc:
        raise _cache_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Screener query failed") from exc
