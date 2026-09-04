"""Full NSE-750 V1/V2 missing-data forensic audit.

Read-only diagnostic. Compares three treatments on the same fresh Yahoo data:
1) V1-style Close + forward-fill
2) V2 Adj Close + no fill
3) Adj Close with each stock aligned to its latest valid observation
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
from src.quant import MOMENTUM_MONTHS, MOMENTUM_WEIGHTS, latest_sharpe, momentum_score  # noqa: E402

OUT = ROOT / "audit_output"
# Horizons are calendar months (1M/3M/6M/9M/12M).
MONTHS = tuple(MOMENTUM_MONTHS)
WEIGHTS = dict(zip(MONTHS, MOMENTUM_WEIGHTS))
# Approximate NSE session counts, used only for the missing-data row tallies.
SESSIONS_PER_MONTH = 21


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
    out = close.copy()
    threshold = max(1, int(np.ceil(out.shape[1] * 0.30)))
    out = out.loc[out.notna().sum(axis=1) >= threshold]
    return out.ffill()


def latest_valid_score(adj: pd.DataFrame) -> pd.Series:
    """Calculate momentum independently on each stock's contiguous valid history.

    This represents latest-valid-date alignment: each stock's own latest valid
    observation is treated as its as-of point, rather than imputing a missing
    common-date observation. Cross-sectional Z-scoring is then done per window.
    """
    components: dict[int, pd.Series] = {}
    for months in MONTHS:
        vals = {}
        for symbol in adj.columns:
            s = adj[symbol].dropna()
            if s.empty:
                vals[symbol] = np.nan
                continue
            # Each stock's own last valid observation is its as-of point, so the
            # calendar window is measured back from that date rather than from
            # the common market date.
            value = latest_sharpe(s.to_frame(name=symbol), months).iloc[0]
            vals[symbol] = float(value) if pd.notna(value) else np.nan
        raw = pd.Series(vals, dtype=float)
        z = (raw - raw.mean()) / raw.std(ddof=1)
        components[months] = z.clip(-3, 3)
    score = sum(components[m] * WEIGHTS[m] for m in MONTHS)
    return score


def main() -> None:
    universe = load_universe()
    symbols = universe["Symbol"].astype(str).str.upper().drop_duplicates().tolist()
    if len(symbols) < 600:
        raise RuntimeError(f"Universe unexpectedly small: {len(symbols)}")

    close, adj = download(symbols)
    as_of = adj.index[adj.notna().any(axis=1)][-1]
    cutoff = as_of - pd.DateOffset(years=2)
    close = close.loc[(close.index >= cutoff) & (close.index <= as_of)]
    adj = adj.loc[(adj.index >= cutoff) & (adj.index <= as_of)]

    v1 = v1_clean(close)
    v2 = adj

    s1 = momentum_score(v1).iloc[-1]
    s2 = momentum_score(v2).iloc[-1]
    s3 = latest_valid_score(v2)
    r1 = s1.rank(ascending=False, method="min", na_option="bottom")
    r2 = s2.rank(ascending=False, method="min", na_option="bottom")
    r3 = s3.rank(ascending=False, method="min", na_option="bottom")

    rows = []
    for symbol in symbols:
        a = v2[symbol]
        b = v1[symbol]
        latest_date = a.dropna().index[-1] if a.notna().any() else pd.NaT
        rec = {
            "Symbol": symbol, "V1 Score": s1.get(symbol), "V2 Score": s2.get(symbol), "LatestValid Score": s3.get(symbol),
            "V1 Rank": r1.get(symbol), "V2 Rank": r2.get(symbol), "LatestValid Rank": r3.get(symbol),
            "V1 Rows": int(b.notna().sum()), "V2 Rows": int(a.notna().sum()),
            "V2 Missing Total": int(a.isna().sum()), "Latest Valid Date": latest_date,
            "V1-V2 Rank Change": r2.get(symbol) - r1.get(symbol),
            "V1-LatestValid Rank Change": r3.get(symbol) - r1.get(symbol),
            "V2-LatestValid Rank Change": r3.get(symbol) - r2.get(symbol),
        }
        for months in MONTHS:
            recent = a.tail(months * SESSIONS_PER_MONTH)
            rec[f"Missing Last {months}M"] = int(recent.isna().sum())
            rec[f"Valid Last {months}M"] = int(recent.notna().sum())
            rec[f"V2 Sharpe {months}M NaN"] = bool(pd.isna(latest_sharpe(v2[[symbol]], months).iloc[0]))
        rows.append(rec)

    report = pd.DataFrame(rows).sort_values(["V2 Rank", "Symbol"], na_position="last")
    OUT.mkdir(exist_ok=True)
    report.to_csv(OUT / "full_nse750_row_audit.csv", index=False)

    def nbig(col: str, threshold: float = 10) -> int:
        return int((report[col].abs() > threshold).sum())

    print(f"Universe: {len(symbols)}")
    print(f"Market as-of: {as_of.date()}")
    print(f"V2 missing last 6M: {int((report['Missing Last 6M'] > 0).sum())}")
    print(f"V2 missing last 12M: {int((report['Missing Last 12M'] > 0).sum())}")
    print(f"V2 NaN 6M Sharpe: {int(report['V2 Sharpe 6M NaN'].sum())}")
    print(f"V2 NaN 12M Sharpe: {int(report['V2 Sharpe 12M NaN'].sum())}")
    print(f"V2 zero/NaN Score: {int((report['V2 Score'].isna() | (report['V2 Score'] == 0)).sum())}")
    print(f"|V1-V2 rank change| >10: {nbig('V1-V2 Rank Change')}")
    print(f"|V1-LatestValid rank change| >10: {nbig('V1-LatestValid Rank Change')}")
    print(f"|V2-LatestValid rank change| >10: {nbig('V2-LatestValid Rank Change')}")

    top = report.assign(abs_lv=report['V1-LatestValid Rank Change'].abs()).sort_values('abs_lv', ascending=False)
    print("\nLargest V1 vs LatestValid rank changes:")
    print(top[["Symbol", "V1 Rank", "V2 Rank", "LatestValid Rank", "V1 Score", "V2 Score", "LatestValid Score", "Latest Valid Date", "Missing Last 6M"]].head(30).to_string(index=False))

    with (OUT / "full_nse750_row_audit_summary.md").open("w", encoding="utf-8") as f:
        f.write(f"# Full NSE-750 missing-data treatment comparison\n\nMarket as-of: {as_of.date()}\n\n")
        f.write(f"- Universe: {len(symbols)}\n")
        f.write(f"- V2 missing last 6M: {int((report['Missing Last 6M'] > 0).sum())}\n")
        f.write(f"- V2 missing last 12M: {int((report['Missing Last 12M'] > 0).sum())}\n")
        f.write(f"- V2 NaN 6M Sharpe: {int(report['V2 Sharpe 6M NaN'].sum())}\n")
        f.write(f"- V2 NaN 12M Sharpe: {int(report['V2 Sharpe 12M NaN'].sum())}\n")
        f.write(f"- V2 zero/NaN score: {int((report['V2 Score'].isna() | (report['V2 Score'] == 0)).sum())}\n")
        f.write(f"- |V1-LatestValid rank change| >10: {nbig('V1-LatestValid Rank Change')}\n")
        f.write(f"- |V2-LatestValid rank change| >10: {nbig('V2-LatestValid Rank Change')}\n\n")
        f.write("Latest-valid alignment drops each stock's missing observations before taking its trailing window; it does not modify production code.\n")


if __name__ == "__main__":
    main()
