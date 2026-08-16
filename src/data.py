from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

import pandas as pd
import requests
import yfinance as yf

from .config import HTTP_HEADERS, NIFTY_TOTAL_MARKET_LOCAL, NIFTY_TOTAL_MARKET_URL


def load_universe(local_path: Path = NIFTY_TOTAL_MARKET_LOCAL) -> pd.DataFrame:
    """Load the NSE Total Market constituent list, preferring live NSE Indices data."""
    try:
        response = requests.get(NIFTY_TOTAL_MARKET_URL, headers=HTTP_HEADERS, timeout=20)
        response.raise_for_status()
        if len(response.content) > 200:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(response.content)
            return _parse_universe(response.content)
    except requests.RequestException:
        pass

    if local_path.exists():
        return _parse_universe(local_path.read_bytes())
    raise FileNotFoundError("NIFTY Total Market constituent file is unavailable")


def _parse_universe(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [str(c).strip() for c in df.columns]
    symbol_col = next((c for c in df.columns if c.lower() in {"symbol", "ticker"}), None)
    name_col = next((c for c in df.columns if "company" in c.lower() or "name" in c.lower()), None)
    industry_col = next((c for c in df.columns if c.lower() in {"industry", "sector", "macro economic sector"}), None)
    if symbol_col is None:
        raise ValueError(f"Could not identify symbol column: {list(df.columns)}")

    out = pd.DataFrame({"Symbol": df[symbol_col].astype(str).str.strip().str.upper()})
    out["Company Name"] = df[name_col].astype(str).str.strip() if name_col else out["Symbol"]
    out["Industry"] = df[industry_col].astype(str).str.strip() if industry_col else "Other"
    out = out[~out["Symbol"].str.startswith("DUMMY")]
    return out.drop_duplicates("Symbol").reset_index(drop=True)


def fetch_ohlcv(symbols: Sequence[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """Download daily OHLCV and normalize yfinance's MultiIndex output."""
    tickers = [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]
    if not tickers:
        return {k: pd.DataFrame() for k in ("open", "high", "low", "close", "volume")}
    raw = yf.download(tickers, period=period, auto_adjust=False, progress=False, group_by="column", threads=True)
    if raw.empty:
        return {k: pd.DataFrame() for k in ("open", "high", "low", "close", "volume")}

    result: dict[str, pd.DataFrame] = {}
    for field in ("Open", "High", "Low", "Close", "Volume"):
        if isinstance(raw.columns, pd.MultiIndex):
            level0 = [str(x) for x in raw.columns.get_level_values(0)]
            if field in level0:
                frame = raw[field].copy()
            else:
                frame = pd.DataFrame(index=raw.index)
        else:
            frame = raw[[field]].copy() if field in raw.columns else pd.DataFrame(index=raw.index)
        frame.columns = [str(c).replace(".NS", "").upper() for c in frame.columns]
        result[field.lower()] = frame.sort_index()
    return result
