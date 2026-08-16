from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

MOMENTUM_WINDOWS = (21, 63, 126, 189, 252)
DEFAULT_LOOKBACK_WEIGHTS = (0.10, 0.30, 0.30, 0.20, 0.10)
BENCHMARK = "^NSEI"
INDEX_UNIVERSE = "NIFTY 750"
MIN_HISTORY = 63

# These five official NSE broad-market constituent sets are intended to form
# the research universe: 50 + 50 + 150 + 250 + 250 = 750 stocks.
INDEX_URLS = {
    "NIFTY 50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "NIFTY NEXT 50": "https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
    "NIFTY MIDCAP 150": "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    "NIFTY SMALLCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
    "NIFTY MICROCAP 250": "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv",
}

INDEX_LOCAL_PATHS = {
    name: DATA_DIR / "indices" / f"{name.lower().replace(' ', '_')}.csv"
    for name in INDEX_URLS
}

# Compatibility aliases for older imports.
NIFTY_TOTAL_MARKET_URL = "https://niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv"
NIFTY_TOTAL_MARKET_LOCAL = DATA_DIR / "indices" / "ind_niftytotalmarket_list.csv"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}
