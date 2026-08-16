from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Sequence

import pandas as pd
import requests
import yfinance as yf

from .config import (
    EXPECTED_INDEX_COUNTS,
    HTTP_HEADERS,
    INDEX_LOCAL_PATHS,
    INDEX_URLS,
    NSE_HOME_URL,
    NSE_REQUEST_RETRIES,
    NSE_REQUEST_TIMEOUT,
)


def _download_nse_csv(url: str) -> bytes:
    """Download an NSE constituent CSV using a browser-like session.

    NSE can reject a direct CSV request even when the URL is valid. Prime the
    session on the public site first so cookies/session state are established,
    then request the CSV with the same session and headers. Retry transient
    403/429/5xx responses before failing so callers can fall back to the last
    locally cached constituent file.
    """
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    last_error: Exception | None = None

    for attempt in range(1, NSE_REQUEST_RETRIES + 1):
        try:
            # Establish NSE session/cookies before the CSV request.
            home = session.get(NSE_HOME_URL, timeout=NSE_REQUEST_TIMEOUT)
            home.raise_for_status()

            response = session.get(url, timeout=NSE_REQUEST_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if len(response.content) <= 200:
                raise ValueError("NSE response was unexpectedly small")
            # A blocked request may return an HTML challenge/login page with
            # a 200 status. Reject obvious HTML so it cannot be cached as CSV.
            if "text/html" in content_type or response.content.lstrip().lower().startswith(b"<!doctype html"):
                raise ValueError("NSE returned HTML instead of the requested CSV")
            return response.content
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < NSE_REQUEST_RETRIES:
                time.sleep(attempt)

    raise RuntimeError(f"Unable to download NSE constituent CSV: {last_error}")


def load_universe() -> pd.DataFrame:
    """Load the canonical Umiya 750 universe from official NSE index files.

    The source sets are Nifty 50, Nifty Next 50, Nifty Midcap 150,
    Nifty Smallcap 250 and Nifty Microcap 250. They are concatenated and
    de-duplicated by Symbol while preserving the source index as a column.
    """
    frames: list[pd.DataFrame] = []
    errors: list[str] = []

    for index_name, url in INDEX_URLS.items():
        local_path = INDEX_LOCAL_PATHS[index_name]
        frame: pd.DataFrame | None = None
        try:
            raw = _download_nse_csv(url)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(raw)
            frame = _parse_universe(raw)
        except (requests.RequestException, RuntimeError, ValueError, pd.errors.ParserError) as exc:
            if local_path.exists():
                try:
                    frame = _parse_universe(local_path.read_bytes())
                    errors.append(f"{index_name}: live download failed; used cached constituent file")
                except Exception as local_exc:
                    errors.append(f"{index_name}: {local_exc}")
            else:
                errors.append(f"{index_name}: {exc}")

        if frame is None:
            continue

        expected = EXPECTED_INDEX_COUNTS[index_name]
        actual = len(frame)
        if actual < max(1, expected - 5) or actual > expected + 5:
            errors.append(f"{index_name}: expected about {expected}, parsed {actual}")
        frame["Index"] = index_name
        frames.append(frame)

    if len(frames) != len(INDEX_URLS):
        detail = " " + "; ".join(errors) if errors else ""
        raise FileNotFoundError("One or more NSE 750 constituent files are unavailable." + detail)

    universe = pd.concat(frames, ignore_index=True)
    duplicate_symbols = universe.loc[universe["Symbol"].duplicated(keep=False), "Symbol"].unique()
    universe = universe.drop_duplicates("Symbol", keep="first").reset_index(drop=True)

    if len(universe) < 700:
        detail = f" Parsed {len(universe)} symbols."
        if errors:
            detail += " " + "; ".join(errors)
        raise ValueError("NSE 750 universe is unexpectedly incomplete." + detail)

    universe.attrs["source_counts"] = {
        name: int((universe["Index"] == name).sum()) for name in INDEX_URLS
    }
    universe.attrs["duplicate_symbols"] = [str(x) for x in duplicate_symbols]
    universe.attrs["warnings"] = errors
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
    raw = yf.download(
        tickers, period=period, auto_adjust=False, progress=False,
        group_by="column", threads=True,
    )
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
