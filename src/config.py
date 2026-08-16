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
MIN_HISTORY = 63

# Canonical NSE Indices constituent sources used to build the Umiya 750
# research universe. Nifty 500 consists of Nifty 50 + Next 50 + Midcap 150
# + Smallcap 250; Nifty Microcap 250 adds the next microcap segment.
INDEX_URLS = {
    "NIFTY 50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "NIFTY NEXT 50": "https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
    "NIFTY MIDCAP 150": "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    "NIFTY SMALLCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
    "NIFTY MICROCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
}

EXPECTED_INDEX_COUNTS = {
    "NIFTY 50": 50,
    "NIFTY NEXT 50": 50,
    "NIFTY MIDCAP 150": 150,
    "NIFTY SMALLCAP 250": 250,
    "NIFTY MICROCAP 250": 250,
}

INDEX_LOCAL_PATHS = {
    name: DATA_DIR / "indices" / f"{name.lower().replace(' ', '_')}.csv"
    for name in INDEX_URLS
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}
