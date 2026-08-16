from __future__ import annotations

import io
import time
from typing import Sequence

import pandas as pd
import requests
import yfinance as yf

from .config import (
    EXPECTED_INDEX_COUNTS,
    HTTP_HEADERS,
    INDEX_LOCAL_PATHS,
    INDEX_URLS,
    MAX_DATA_AGE_DAYS,
    MIN_HISTORY,
    NSE_HOME_URL,
    NSE_REQUEST_RETRIES,
    NSE_REQUEST_TIMEOUT,
)

PRICE_FIELDS = ("adj_close", "volume")
HISTORY_YEARS = 10


def _download_nse_csv(url: str) -> bytes:
    """Download an NSE constituent CSV using a browser-like session."""
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    last_error: Exception | None = None
    for attempt in range(1, NSE_REQUEST_RETRIES + 1):
        try:
            session.get(NSE_HOME_URL, timeout=NSE_REQUEST_TIMEOUT).raise_for_status()
            response = session.get(url, timeout=NSE_REQUEST_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if len(response.content) <= 200:
                raise ValueError("NSE response was unexpectedly small")
            if "text/html" in content_type or response.content.lstrip().lower().startswith(b"<!doctype html"):
                raise ValueError("NSE returned HTML instead of the requested CSV")
            return response.content
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < NSE_REQUEST_RETRIES:
                time.sleep(attempt)
    raise RuntimeError(f"Unable to download NSE constituent CSV: {last_error}")


def load_universe() -> pd.DataFrame:
    """Load the canonical Umiya 750 universe from official NSE index files."""
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
        raise ValueError(f"NSE 750 universe is unexpectedly incomplete. Parsed {len(universe)} symbols.")
    universe.attrs["source_counts"] = {name: int((universe["Index"] == name).sum()) for name in INDEX_URLS}
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
    return out[~out["Symbol"].str.startswith("DUMMY")].drop_duplicates("Symbol").reset_index(drop=True)


def _ten_year_window() -> tuple[str, str]:
    end = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    start = end - pd.DateOffset(years=HISTORY_YEARS)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fetch_prices(symbols: Sequence[str], start: str | None = None, end: str | None = None) -> dict[str, pd.DataFrame]:
    """Download the canonical V2 dataset: 10 years of Adjusted Close and Volume."""
    tickers = [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]
    if not tickers:
        return {field: pd.DataFrame() for field in PRICE_FIELDS}
    default_start, default_end = _ten_year_window()
    raw = yf.download(
        tickers,
        start=start or default_start,
        end=end or default_end,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=True,
    )
    if raw.empty:
        return {field: pd.DataFrame() for field in PRICE_FIELDS}
    if not isinstance(raw.columns, pd.MultiIndex):
        raise ValueError("Expected yfinance MultiIndex output for the NSE-750 download")
    result: dict[str, pd.DataFrame] = {}
    for source_field, output_field in (("Adj Close", "adj_close"), ("Volume", "volume")):
        if source_field not in raw.columns.get_level_values(0):
            raise ValueError(f"Yahoo response is missing required field: {source_field}")
        frame = raw[source_field].copy()
        frame.columns = [str(c).replace(".NS", "").upper() for c in frame.columns]
        frame = frame.reindex(columns=[str(s).replace(".NS", "").upper() for s in symbols])
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        result[output_field] = frame.sort_index()
    return result


def fetch_ohlcv(symbols: Sequence[str], period: str = "10y") -> dict[str, pd.DataFrame]:
    """Temporary compatibility name; returns only the V2 Adj Close + Volume fields."""
    return fetch_prices(symbols)


def latest_market_date(adj_close: pd.DataFrame) -> pd.Timestamp:
    """Return one common market as-of date for the entire universe."""
    valid_dates = adj_close.notna().any(axis=1)
    if not valid_dates.any():
        raise ValueError("Adjusted Close dataset contains no valid observations")
    return pd.Timestamp(adj_close.index[valid_dates][-1]).normalize()


def eligible_symbols(adj_close: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """Find stocks with >=126 observations and latest data <=3 calendar days stale."""
    if adj_close.empty:
        return pd.DataFrame(columns=["Symbol", "History Days", "Last Price Date", "Data Age Days"])
    as_of = pd.Timestamp(as_of or latest_market_date(adj_close)).normalize()
    records = []
    for symbol in adj_close.columns:
        series = adj_close[symbol].dropna()
        if len(series) < MIN_HISTORY:
            continue
        last_date = pd.Timestamp(series.index[-1]).normalize()
        age_days = int((as_of - last_date).days)
        if age_days <= MAX_DATA_AGE_DAYS:
            records.append({"Symbol": symbol, "History Days": int(len(series)), "Last Price Date": last_date, "Data Age Days": age_days})
    return pd.DataFrame(records)


def align_trailing_to_as_of(frame: pd.DataFrame, symbols: Sequence[str], as_of: pd.Timestamp) -> pd.DataFrame:
    """Reindex to the common universe without imputing missing prices or volume.

    The function name is retained temporarily for compatibility with the
    unfinished Phase 3 service. V2 does not forward-fill trailing observations.
    Freshness is validated separately by ``eligible_symbols``.
    """
    return frame.reindex(columns=list(symbols)).copy()
