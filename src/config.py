from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

MOMENTUM_WINDOWS = (21, 63, 126, 189, 252)
DEFAULT_LOOKBACK_WEIGHTS = (0.10, 0.30, 0.30, 0.20, 0.10)
BENCHMARK = "^NSEI"
INDEX_UNIVERSE = "NIFTY TOTAL MARKET"
MIN_HISTORY = 63

NIFTY_TOTAL_MARKET_URL = "https://niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv"
NIFTY_TOTAL_MARKET_LOCAL = DATA_DIR / "indices" / "ind_niftytotalmarket_list.csv"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}
