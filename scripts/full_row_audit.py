"""Full NSE-750 V1-vs-V2 row/missing-data forensic audit.

Read-only diagnostic: downloads fresh Yahoo data, does not publish or modify
canonical datasets. It measures how missing observations affect the current
V2 Sharpe/R² pipeline versus a V1-style Close + forward-fill series.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import load_universe  # noqa: E402
from src.quant import MOMENTUM_WINDOWS, momentum_score, sharpe, rolling_r2  # noqa: E402

OUT = ROOT / "audit_output"
WINDOWS = tuple(MOMENTUM_WINDOWS)


def download(symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    tickers = [f"{s}.NS" for s in symbols]
    end = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    start = end - pd.DateOffset(years=10)
    raw = yf.download(tickers, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                      auto_adjust=False, actions=False, progress=False, group_by="column", threads=True)
    close = raw["Close"].copy()
    adj = raw["Adj Close"].copy()
    for frame in (close, adj):
        frame.columns = [str(c).replace(".NS", "").upper() for c in frame.columns]
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return close.reindex(columns=symbols).sort_index(), adj.reindex(columns=symbols).sort_index()


def v1_clean(close: pd.DataFrame) -> pd.DataFrame:
    # V1-style cleaning: remove rows where >70% of the universe is missing,
    # then forward-fill remaining observations.
    out = close.copy()
    threshold = max(1, int(np.ceil(out.shape[1] * 0.30)))
    out = out.loc[out.notna().sum(axis=1) >= threshold]
    return out.ffill()


def main() -> None:
    universe = load_universe()
    symbols = universe["Symbol"].astype(str).str.upper().drop_duplicates().tolist()
    if len(symbols) < 600:
        raise RuntimeError(f"Universe unexpectedly small: {len(symbols)}")

    close, adj = download(symbols)
    # Use a common latest market date and the trailing 2-year V1 history.
    as_of = adj.index[adj.notna().any(axis=1)][-1]
    cutoff = as_of - pd.DateOffset(years=2)
    close = close.loc[(close.index >= cutoff) & (close.index <= as_of)]
    adj = adj.loc[(adj.index >= cutoff) & (adj.index <= as_of)]

    v1 = v1_clean(close)
    v2 = adj

    s1 = momentum_score(v1).iloc[-1]
    s2 = momentum_score(v2).iloc[-1]
    r1 = s1.rank(ascending=False, method="min", na_option="bottom")
    r2 = s2.rank(ascending=False, method="min", na_option="bottom")

    rows = []
    for symbol in symbols:
        a = v2[symbol]
        b = v1[symbol]
        rec = {"Symbol": symbol, "V1 Score": s1.get(symbol), "V2 Score": s2.get(symbol),
               "V1 Rank": r1.get(symbol), "V2 Rank": r2.get(symbol),
               "V1 Rows": int(b.notna().sum()), "V2 Rows": int(a.notna().sum()),
               "V2 Missing Total": int(a.isna().sum()),
               "V1-V2 Rank Change": (r2.get(symbol) - r1.get(symbol))}
        for w in WINDOWS:
            recent = a.tail(w)
            rec[f"Missing Last {w}"] = int(recent.isna().sum())
            rec[f"Valid Last {w}"] = int(recent.notna().sum())
            # Directly expose whether the current V2 rolling component is NaN.
            rec[f"V2 Sharpe {w} NaN"] = bool(pd.isna(sharpe(v2[[symbol]], w).iloc[-1, 0]))
            rec[f"V2 R2 {w} NaN"] = bool(pd.isna(rolling_r2(v2[[symbol]], w).iloc[-1, 0]))
            rec[f"V1 Sharpe {w} NaN"] = bool(pd.isna(sharpe(v1[[symbol]], w).iloc[-1, 0]))
            rec[f"V1 R2 {w} NaN"] = bool(pd.isna(rolling_r2(v1[[symbol]], w).iloc[-1, 0]))
        rows.append(rec)

    report = pd.DataFrame(rows).sort_values(["V2 Rank", "Symbol"], na_position="last")
    OUT.mkdir(exist_ok=True)
    report.to_csv(OUT / "full_nse750_row_audit.csv", index=False)

    # Compact summary for the Actions log/summary.
    bad_score = report["V2 Score"].isna() | (report["V2 Score"] == 0)
    any_missing_126 = report["Missing Last 126"] > 0
    any_missing_252 = report["Missing Last 252"] > 0
    v2_nan_126 = report["V2 Sharpe 126 NaN"] | report["V2 R2 126 NaN"]
    v2_nan_252 = report["V2 Sharpe 252 NaN"] | report["V2 R2 252 NaN"]

    print(f"Universe: {len(symbols)}")
    print(f"Market as-of: {as_of.date()}")
    print(f"V2 stocks with missing values in last 126 rows: {int(any_missing_126.sum())}")
    print(f"V2 stocks with missing values in last 252 rows: {int(any_missing_252.sum())}")
    print(f"V2 stocks with NaN 6M Sharpe or R²: {int(v2_nan_126.sum())}")
    print(f"V2 stocks with NaN 12M Sharpe or R²: {int(v2_nan_252.sum())}")
    print(f"V2 zero/NaN Momentum Score: {int(bad_score.sum())}")
    print("\nLargest absolute rank changes (top 30):")
    cols = ["Symbol", "V1 Rank", "V2 Rank", "V1 Score", "V2 Score", "V1-V2 Rank Change", "Missing Last 126", "Missing Last 252"]
    print(report.assign(abs_change=report["V1-V2 Rank Change"].abs()).sort_values("abs_change", ascending=False)[cols].head(30).to_string(index=False))

    with (OUT / "full_nse750_row_audit_summary.md").open("w", encoding="utf-8") as f:
        f.write(f"# Full NSE-750 row audit\n\nMarket as-of: {as_of.date()}\n\n")
        f.write(f"- Universe: {len(symbols)}\n- Missing in last 126 rows: {int(any_missing_126.sum())}\n")
        f.write(f"- Missing in last 252 rows: {int(any_missing_252.sum())}\n")
        f.write(f"- V2 NaN 6M Sharpe/R²: {int(v2_nan_126.sum())}\n- V2 NaN 12M Sharpe/R²: {int(v2_nan_252.sum())}\n")
        f.write(f"- V2 zero/NaN Momentum Score: {int(bad_score.sum())}\n\n")
        f.write("See `full_nse750_row_audit.csv` for stock-level results.\n")


if __name__ == "__main__":
    main()
