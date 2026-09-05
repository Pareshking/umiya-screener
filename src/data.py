from __future__ import annotations

import io
import time
from math import ceil
from typing import Sequence

import pandas as pd
import requests
import yfinance as yf

from .config import (
    BENCHMARK,
    EXPECTED_INDEX_COUNTS,
    HTTP_HEADERS,
    INDEX_COUNT_MIN_RATIO,
    INDEX_LOCAL_PATHS,
    INDEX_URLS,
    MAX_DATA_AGE_DAYS,
    MIN_HISTORY,
    NSE_HOME_URL,
    NSE_REQUEST_RETRIES,
    NSE_REQUEST_TIMEOUT,
    UNIVERSE_MIN_RATIO,
    YAHOO_MIN_COVERAGE_RATIO,
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


def _validate_index_count(index_name: str, actual: int) -> str | None:
    """Validate an NSE source count without requiring the nominal count to stay fixed."""
    expected = EXPECTED_INDEX_COUNTS[index_name]
    minimum = max(1, ceil(expected * INDEX_COUNT_MIN_RATIO))
    if actual < minimum:
        raise ValueError(
            f"{index_name}: parsed only {actual} constituents; "
            f"expected about {expected} and at least {minimum} is required"
        )
    if actual != expected:
        return f"{index_name}: constituent count changed from baseline {expected} to {actual}"
    return None


def load_universe() -> pd.DataFrame:
    """Load the canonical Umiya universe from current official NSE index files."""
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
        actual = len(frame)
        count_warning = _validate_index_count(index_name, actual)
        if count_warning:
            errors.append(count_warning)
        frame["Index"] = index_name
        frames.append(frame)
    if len(frames) != len(INDEX_URLS):
        detail = " " + "; ".join(errors) if errors else ""
        raise FileNotFoundError("One or more NSE 750 constituent files are unavailable." + detail)
    universe = pd.concat(frames, ignore_index=True)
    duplicate_symbols = universe.loc[universe["Symbol"].duplicated(keep=False), "Symbol"].unique()
    universe = universe.drop_duplicates("Symbol", keep="first").reset_index(drop=True)
    expected_total = sum(EXPECTED_INDEX_COUNTS.values())
    minimum_total = ceil(expected_total * UNIVERSE_MIN_RATIO)
    if len(universe) < minimum_total:
        raise ValueError(
            f"NSE 750 universe is unexpectedly incomplete. Parsed {len(universe)} unique symbols; "
            f"at least {minimum_total} are required"
        )
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

    requested = [str(s).replace(".NS", "").upper() for s in symbols]
    result: dict[str, pd.DataFrame] = {}
    for source_field, output_field in (("Adj Close", "adj_close"), ("Volume", "volume")):
        if source_field not in raw.columns.get_level_values(0):
            raise ValueError(f"Yahoo response is missing required field: {source_field}")
        frame = raw[source_field].copy()
        frame.columns = [str(c).replace(".NS", "").upper() for c in frame.columns]
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        frame = frame.sort_index()
        available = [symbol for symbol in requested if symbol in frame.columns and frame[symbol].notna().any()]
        coverage = len(available) / len(requested)
        if coverage < YAHOO_MIN_COVERAGE_RATIO:
            missing = [symbol for symbol in requested if symbol not in available]
            sample = ", ".join(missing[:20])
            raise RuntimeError(
                f"Yahoo {source_field} coverage is only {coverage:.1%}; "
                f"minimum is {YAHOO_MIN_COVERAGE_RATIO:.1%}. Missing sample: {sample}"
            )
        result[output_field] = frame.reindex(columns=requested)
    return result


def fetch_benchmark(symbol: str = BENCHMARK, start: str | None = None, end: str | None = None) -> pd.Series:
    """Download the benchmark index close over the same ten-year window.

    Relative strength needs something to be relative to. BENCHMARK was declared
    in config from the start but never actually fetched, so every RS-style
    reading was unavailable rather than wrong.

    The index is returned as a plain Series of closes. Yahoo does not publish an
    Adjusted Close for an index that differs from its Close -- an index has no
    dividends or splits to adjust for -- so Close is the canonical value here.
    """
    default_start, default_end = _ten_year_window()
    raw = yf.download(
        symbol,
        start=start or default_start,
        end=end or default_end,
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"Yahoo returned no history for benchmark {symbol}")
    frame = raw["Close"] if "Close" in raw.columns.get_level_values(0) else None
    if frame is None:
        raise RuntimeError(f"Yahoo benchmark response is missing Close: {symbol}")
    series = frame.iloc[:, 0] if isinstance(frame, pd.DataFrame) else frame
    series.index = pd.to_datetime(series.index).tz_localize(None)
    series = series.sort_index().dropna()
    if series.empty:
        raise RuntimeError(f"Benchmark {symbol} has no usable closes")
    return series.rename("benchmark")


def fetch_ohlcv(symbols: Sequence[str], period: str = "10y") -> dict[str, pd.DataFrame]:
    """Temporary compatibility name; returns only the V2 Adj Close + Volume fields."""
    return fetch_prices(symbols)


def latest_market_date(adj_close: pd.DataFrame) -> pd.Timestamp:
    """Return one common market as-of date for the entire universe."""
    valid_dates = adj_close.notna().any(axis=1)
    if not valid_dates.any():
        raise ValueError("Adjusted Close dataset contains no valid observations")
    return pd.Timestamp(adj_close.index[valid_dates][-1]).normalize()


def eligible_symbols(
    adj_close: pd.DataFrame,
    volume: pd.DataFrame | None = None,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Find stocks with sufficient history and fresh price/volume observations."""
    price_only = volume is None
    columns = ["Symbol", "History Days", "Last Price Date", "Data Age Days", "Volume Days", "Last Volume Date", "Volume Age Days"]
    if adj_close.empty:
        return pd.DataFrame(columns=columns)
    if volume is None:
        volume = adj_close
    volume = volume.reindex(index=adj_close.index, columns=adj_close.columns)
    as_of = pd.Timestamp(as_of or latest_market_date(adj_close)).normalize()
    records = []
    for symbol in adj_close.columns:
        price_series = adj_close[symbol].dropna()
        volume_series = volume[symbol].dropna()
        if len(price_series) < MIN_HISTORY or len(volume_series) < MIN_HISTORY:
            continue
        last_price_date = pd.Timestamp(price_series.index[-1]).normalize()
        last_volume_date = pd.Timestamp(volume_series.index[-1]).normalize()
        price_age = int((as_of - last_price_date).days)
        volume_age = int((as_of - last_volume_date).days)
        if price_age > MAX_DATA_AGE_DAYS:
            continue
        if not price_only and volume_age > MAX_DATA_AGE_DAYS:
            continue
        records.append(
            {
                "Symbol": symbol,
                "History Days": int(len(price_series)),
                "Last Price Date": last_price_date,
                "Data Age Days": price_age,
                "Volume Days": int(len(volume_series)),
                "Last Volume Date": last_volume_date,
                "Volume Age Days": volume_age,
            }
        )
    return pd.DataFrame(records, columns=columns)


def align_trailing_to_as_of(frame: pd.DataFrame, symbols: Sequence[str], as_of: pd.Timestamp) -> pd.DataFrame:
    """Reindex to the common universe without imputing missing prices or volume."""
    return frame.reindex(columns=list(symbols)).copy()
