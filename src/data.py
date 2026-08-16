from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

import pandas as pd
import requests
import yfinance as yf

from .config import HTTP_HEADERS, INDEX_LOCAL_PATHS, INDEX_URLS


def load_universe() -> pd.DataFrame:
    """Load the intended NSE 750 universe from the five official index files.

    The source sets are Nifty 50, Nifty Next 50, Nifty Midcap 150,
    Nifty Smallcap 250 and Nifty Microcap 250. They are concatenated and
    de-duplicated by Symbol while preserving the source index as a column.
    """
    frames: list[pd.DataFrame] = []
    errors: list[str] = []

    for index_name, url in INDEX_URLS.items():
        local_path = INDEX_LOCAL_PATHS[index_name]
        try:
            response = requests.get(url, headers=HTTP_HEADERS, timeout=20)
            response.raise_for_status()
            if len(response.content) <= 200:
                raise ValueError("response was unexpectedly small")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(response.content)
            frame = _parse_universe(response.content)
        except (requests.RequestException, ValueError, pd.errors.ParserError) as exc:
            if local_path.exists():
                try:
                    frame = _parse_universe(local_path.read_bytes())
                except Exception as local_exc:
                    errors.append(f"{index_name}: {local_exc}")
                    continue
            else:
                errors.append(f"{index_name}: {exc}")
                continue

        frame["Index"] = index_name
        frames.append(frame)

    if not frames:
        raise FileNotFoundError("No NSE 750 constituent files are available")

    universe = pd.concat(frames, ignore_index=True)
    # The five official source sets should be disjoint. If NSE data ever
    # contains an overlap, keep the first occurrence and make the issue visible.
    universe = universe.drop_duplicates("Symbol", keep="first").reset_index(drop=True)

    if len(universe) < 700:
        detail = f" Parsed {len(universe)} symbols."
        if errors:
            detail += " " + "; ".join(errors)
        raise ValueError("NSE 750 universe is unexpectedly incomplete." + detail)

    return universe


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
