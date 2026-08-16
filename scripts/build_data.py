"""Build and atomically publish the canonical Umiya V2 price dataset."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import HISTORY_YEARS, PRICE_FIELDS, eligible_symbols, fetch_prices, latest_market_date, load_universe

OUTPUT_ROOT = ROOT / "data_cache" / "price_history"


def build() -> tuple[Path, dict]:
    universe = load_universe()
    symbols = universe["Symbol"].astype(str).str.upper().drop_duplicates().tolist()
    if len(symbols) != 750:
        raise RuntimeError(f"Expected canonical NSE 750 universe, received {len(symbols)} symbols")

    data = fetch_prices(symbols)
    if set(data) != set(PRICE_FIELDS):
        raise RuntimeError(f"Unexpected price fields: {sorted(data)}")
    adj_close = data["adj_close"].reindex(columns=symbols)
    volume = data["volume"].reindex(columns=symbols)
    if adj_close.empty or volume.empty:
        raise RuntimeError("Yahoo returned an empty canonical dataset")

    as_of = latest_market_date(adj_close)
    eligibility = eligible_symbols(adj_close, as_of=as_of)
    eligible = set(eligibility["Symbol"])
    if not eligible:
        raise RuntimeError("No stocks satisfy the Phase 1 history/freshness rules")

    missing_required_fields = [symbol for symbol in eligibility["Symbol"] if volume[symbol].notna().sum() < 126]
    if missing_required_fields:
        raise RuntimeError("Eligible stocks without 126 valid volume observations: " + ", ".join(missing_required_fields))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = OUTPUT_ROOT / f"dataset_{timestamp}.tmp"
    published = OUTPUT_ROOT / f"dataset_{timestamp}"
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        adj_close.to_parquet(candidate / "adj_close.parquet")
        volume.to_parquet(candidate / "volume.parquet")
        eligibility.to_parquet(candidate / "eligibility.parquet", index=False)
        universe.to_parquet(candidate / "universe.parquet", index=False)
        metadata = {
            "schema_version": "1.1",
            "data_contract": ["adj_close", "volume"],
            "history_years": HISTORY_YEARS,
            "universe": "NIFTY 750",
            "universe_symbols": len(symbols),
            "eligible_symbols": len(eligible),
            "market_as_of": as_of.strftime("%Y-%m-%d"),
            "max_data_age_days": 3,
            "min_history_observations": 126,
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "Yahoo Finance / yfinance",
            "nse_source_warnings": universe.attrs.get("warnings", []),
            "duplicate_symbols": universe.attrs.get("duplicate_symbols", []),
            "source_counts": universe.attrs.get("source_counts", {}),
        }
        (candidate / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        candidate.replace(published)
    except Exception:
        import shutil
        shutil.rmtree(candidate, ignore_errors=True)
        raise

    latest_tmp = OUTPUT_ROOT / "LATEST.tmp.json"
    latest_tmp.write_text(json.dumps({"dataset": published.name}, indent=2), encoding="utf-8")
    latest_tmp.replace(OUTPUT_ROOT / "LATEST.json")
    return published, metadata


if __name__ == "__main__":
    path, metadata = build()
    print(json.dumps({"published_path": str(path), **metadata}, indent=2))
