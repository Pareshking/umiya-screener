"""Live Yahoo contract probe for a newly injected NSE symbol.

This is intentionally opt-in: it exercises the real Yahoo source without making
CI dependent on a third-party market-data request.

Usage:
    python scripts/probe_yahoo_injected_stock.py APCOTEXIND
"""

from __future__ import annotations

import sys

from src.data import MIN_HISTORY, fetch_prices, eligible_symbols


def main(symbol: str = "APCOTEXIND") -> None:
    symbol = symbol.upper().replace(".NS", "")
    data = fetch_prices([symbol])
    close = data["adj_close"]
    volume = data["volume"]
    assert symbol in close.columns and symbol in volume.columns, f"Yahoo did not return {symbol}"
    assert close[symbol].notna().sum() >= MIN_HISTORY, f"{symbol}: insufficient price history"
    assert volume[symbol].notna().sum() >= MIN_HISTORY, f"{symbol}: insufficient volume history"
    eligible = eligible_symbols(close)
    assert symbol in set(eligible["Symbol"]), f"{symbol}: failed freshness/history eligibility"
    print({
        "symbol": symbol,
        "history_days": int(close[symbol].notna().sum()),
        "volume_days": int(volume[symbol].notna().sum()),
        "last_price_date": str(close[symbol].dropna().index[-1].date()),
        "last_adj_close": float(close[symbol].dropna().iloc[-1]),
        "status": "PASS",
    })


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "APCOTEXIND")
