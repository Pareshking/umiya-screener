"""Read-only audit of the canonical production dataset and metrics.

This script does not modify production calculations or publish anything. It is
intended to run immediately after the scheduled data/metrics build so we can
trace ranking anomalies back to the actual canonical rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.quant import latest_sharpe, period_window, returns  # noqa: E402

SYMBOLS = ["CUPID", "STLTECH", "LAURUSLABS", "ATHERENERG", "RRKABEL"]


def latest_dataset(root: Path, kind: str) -> Path:
    base = root / "data_cache" / kind
    pointer = json.loads((base / "LATEST.json").read_text(encoding="utf-8"))
    return base / pointer["dataset"]


def audit_symbol(close: pd.DataFrame, metrics: pd.DataFrame, symbol: str) -> dict:
    s = close[symbol]
    last_126 = s.tail(126)
    last_252 = s.tail(252)
    # Horizons are calendar months. Recompute against the whole universe so the
    # window anchors on the same market dates production used.
    six_month_window = period_window(close, 6)
    six_month_return = returns(close).loc[symbol, "6M Return"]
    sharpe_6m = latest_sharpe(close[[symbol]], 6).iloc[0]
    row = metrics.loc[metrics["Symbol"].astype(str).str.upper() == symbol]
    m = row.iloc[0] if not row.empty else None
    return {
        "symbol": symbol,
        "total_rows": int(len(s)),
        "total_valid_rows": int(s.notna().sum()),
        "last_date": str(s.index[-1].date()) if len(s) else None,
        "last_126_rows": int(len(last_126)),
        "last_126_valid": int(last_126.notna().sum()),
        "last_126_missing": int(last_126.isna().sum()),
        "last_252_rows": int(len(last_252)),
        "last_252_valid": int(last_252.notna().sum()),
        "last_252_missing": int(last_252.isna().sum()),
        "6m_window_target_start": str(six_month_window["target_start"].date()),
        "6m_window_actual_start": str(six_month_window["actual_start"].date()),
        "6m_window_observations": int(six_month_window["observations"]),
        "6m_return_pct": float(six_month_return) if pd.notna(six_month_return) else None,
        "6m_sharpe_recomputed": float(sharpe_6m) if pd.notna(sharpe_6m) else None,
        "production_6m_return_pct": float(m["6M Return"]) if m is not None and pd.notna(m.get("6M Return")) else None,
        "production_6m_sharpe": float(m["6M Sharpe"]) if m is not None and pd.notna(m.get("6M Sharpe")) else None,
        "production_momentum_score": float(m["Momentum Score"]) if m is not None and pd.notna(m.get("Momentum Score")) else None,
        "production_rank": int(m["Rank"]) if m is not None and pd.notna(m.get("Rank")) else None,
        "production_market_as_of": str(m["Market As Of"]) if m is not None else None,
    }


def main() -> None:
    price_dataset = latest_dataset(ROOT, "price_history")
    metrics_dataset = latest_dataset(ROOT, "metrics")
    close = pd.read_parquet(price_dataset / "adj_close.parquet")
    metrics = pd.read_parquet(metrics_dataset / "screener_metrics.parquet")
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index()
    missing_symbols = [s for s in SYMBOLS if s not in close.columns]
    if missing_symbols:
        raise SystemExit(f"Audit symbols missing from canonical dataset: {missing_symbols}")

    results = [audit_symbol(close, metrics, symbol) for symbol in SYMBOLS]
    metadata = json.loads((price_dataset / "metadata.json").read_text(encoding="utf-8"))
    metrics_metadata = json.loads((metrics_dataset / "metadata.json").read_text(encoding="utf-8"))
    report = {
        "price_dataset": price_dataset.name,
        "metrics_dataset": metrics_dataset.name,
        "price_market_as_of": metadata.get("market_as_of"),
        "price_built_at_utc": metadata.get("built_at_utc"),
        "metrics_built_at_utc": metrics_metadata.get("built_at_utc"),
        "rows": len(close),
        "columns": len(close.columns),
        "stocks": results,
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
