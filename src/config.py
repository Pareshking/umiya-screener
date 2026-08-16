from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)
METRICS_CACHE_PATH = CACHE_DIR / "screener_metrics.parquet"
METRICS_CACHE_TTL_HOURS = 24

MOMENTUM_WINDOWS = (21, 63, 126, 189, 252)
DEFAULT_LOOKBACK_WEIGHTS = (0.10, 0.30, 0.30, 0.20, 0.10)
BENCHMARK = "^NSEI"
INDEX_UNIVERSE = "NIFTY 750"
MIN_HISTORY = 126
# A stock may be behind the common market as-of date by at most three
# calendar days (weekends/exchange holidays are represented by the common
# market date, so they do not create fake observations).
MAX_DATA_AGE_DAYS = 3

# A Yahoo response that silently loses a large part of the requested universe
# is treated as a failed build rather than publishing a deceptively small set.
YAHOO_MIN_COVERAGE_RATIO = 0.90

INDEX_URLS = {
    "NIFTY 50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "NIFTY NEXT 50": "https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
    "NIFTY MIDCAP 150": "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    "NIFTY SMALLCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
    "NIFTY MICROCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
}

# These are baseline/reference counts, not hard requirements. NSE can have
# legitimate constituent-count changes (for example, additional securities
# such as a DVR can make the security count exceed the nominal company count).
EXPECTED_INDEX_COUNTS = {
    "NIFTY 50": 50,
    "NIFTY NEXT 50": 50,
    "NIFTY MIDCAP 150": 150,
    "NIFTY SMALLCAP 250": 250,
    "NIFTY MICROCAP 250": 250,
}

# Protect the pipeline from catastrophically incomplete constituent files while
# still allowing legitimate count changes above this floor.
INDEX_COUNT_MIN_RATIO = 0.80
UNIVERSE_MIN_RATIO = 0.80

INDEX_LOCAL_PATHS = {
    name: DATA_DIR / "indices" / f"{name.lower().replace(' ', '_')}.csv"
    for name in INDEX_URLS
}

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.niftyindices.com/",
    "Connection": "keep-alive",
}
NSE_HOME_URL = "https://www.niftyindices.com/"
NSE_REQUEST_TIMEOUT = 30
NSE_REQUEST_RETRIES = 3
