"""Build and atomically publish the canonical Umiya V2 price dataset."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import BENCHMARK, MIN_HISTORY, MAX_DATA_AGE_DAYS
from src.data import HISTORY_YEARS, PRICE_FIELDS, eligible_symbols, fetch_benchmark, fetch_prices, latest_market_date, load_universe

OUTPUT_ROOT = ROOT / "data_cache" / "price_history"
MIN_UNIVERSE = 600


def build() -> tuple[Path, dict]:
    universe = load_universe()
    symbols = universe["Symbol"].astype(str).str.upper().drop_duplicates().tolist()
    if len(symbols) < MIN_UNIVERSE:
        raise RuntimeError(f"Canonical NSE universe is incomplete: received only {len(symbols)} symbols")

    data = fetch_prices(symbols)
    if set(data) != set(PRICE_FIELDS):
        raise RuntimeError(f"Unexpected price fields: {sorted(data)}")
    adj_close = data["adj_close"].reindex(columns=symbols)
    volume = data["volume"].reindex(columns=symbols)
    if adj_close.empty or volume.empty:
        raise RuntimeError("Yahoo returned an empty canonical dataset")

    # The benchmark drives relative strength on the stock page. A failure here
    # must not sink the whole dataset: RS is one panel, the screener is the app.
    try:
        benchmark = fetch_benchmark()
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"WARNING: benchmark unavailable, relative strength will be omitted: {exc}")
        benchmark = None

    as_of = latest_market_date(adj_close)
    eligibility = eligible_symbols(adj_close, volume=volume, as_of=as_of)
    eligible = set(eligibility["Symbol"])
    if not eligible:
        raise RuntimeError("No stocks satisfy the Phase 1 history/freshness rules")

    # Never publish a suspiciously small result caused by a broad provider
    # failure. Individual securities can legitimately be excluded, but a large
    # collapse in eligible coverage is a build failure, not a valid market state.
    eligible_ratio = len(eligible) / len(symbols)
    if eligible_ratio < 0.80:
        raise RuntimeError(
            f"Only {len(eligible)}/{len(symbols)} ({eligible_ratio:.1%}) securities are eligible; "
            "refusing to publish an incomplete dataset"
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = OUTPUT_ROOT / f"dataset_{timestamp}.tmp"
    published = OUTPUT_ROOT / f"dataset_{timestamp}"
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        adj_close.to_parquet(candidate / "adj_close.parquet")
        volume.to_parquet(candidate / "volume.parquet")
        if benchmark is not None:
            benchmark.to_frame(name="close").to_parquet(candidate / "benchmark.parquet")
        eligibility.to_parquet(candidate / "eligibility.parquet", index=False)
        universe.to_parquet(candidate / "universe.parquet", index=False)
        metadata = {
            "schema_version": "1.2",
            "data_contract": ["adj_close", "volume"],
            "benchmark": BENCHMARK if benchmark is not None else None,
            "history_years": HISTORY_YEARS,
            "universe": "NIFTY 750",
            "universe_symbols": len(symbols),
            "eligible_symbols": len(eligible),
            "eligible_ratio": eligible_ratio,
            "market_as_of": as_of.strftime("%Y-%m-%d"),
            "max_data_age_days": MAX_DATA_AGE_DAYS,
            "min_history_observations": MIN_HISTORY,
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
