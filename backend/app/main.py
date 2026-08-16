from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ScreenerQuery
from .service import FILTERABLE, store, query

app = FastAPI(title="Umiya Screener API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "built_at": store.built_at.isoformat() if store.built_at else None}


@app.get("/api/v1/screener/metadata")
def metadata() -> dict:
    frame = store.get()
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/screener/refresh")
def refresh() -> dict:
    store.get(force=True)
    return {"status": "refreshed", "built_at": store.built_at.isoformat() if store.built_at else None}
