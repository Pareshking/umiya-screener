# Umiya V2 — Data Quality & Missing-Data Policy

This document is part of the V2 source of truth. It defines how the screener treats exchange calendars, partial stock history, and NSE constituent downloads.

## 1. Exchange holidays and weekends

Weekends and exchange holidays are **not missing observations**. They normally do not appear as rows in the daily OHLCV source and must not cause a data-quality failure.

Do not manufacture Saturday/Sunday/holiday rows merely to make the index continuous.

## 2. Missing observations for individual stocks

A missing price for one stock must **not delete the trading-date row for the rest of the universe**.

The quantitative engine must tolerate per-symbol missing observations and calculate each metric from the valid observations available for that symbol.

Do not globally forward-fill prices. A stale carried-forward price can create artificial zero returns and contaminate momentum, volatility and R².

## 3. Minimum stock history

A stock is eligible for the Screener when it has at least **126 valid daily price observations**.

A stock with fewer than 126 valid observations is excluded from the Screener ranking/results, but its missing history must not cause the entire pipeline to fail.

The minimum-history rule is about **valid observations**, not calendar days.

## 4. Longer lookbacks

Having only 126 valid observations does **not** make a stock unusable.

Longer metrics may be unavailable for newer stocks. Missing longer-lookback components must not disqualify an otherwise eligible stock.

For the current Umiya policy:

- 1M and 3M can be calculated from the available 126-day history.
- 6M can be calculated when 126 valid observations are available.
- 9M may be unavailable when sufficient history does not exist.
- **12M RoC is explicitly defined as 0 when a full 12M history is unavailable.**
- Missing components of the weighted momentum score contribute zero rather than causing the eligible stock to disappear.

Any future change to this policy must be an explicit methodology decision, not an accidental consequence of implementation.

## 5. No silent data fabrication

The following are prohibited:

- fabricating prices
- filling missing prices with arbitrary values
- treating a missing 12M return as a positive/negative estimate
- silently substituting unrelated symbols
- silently replacing failed live data with fake values

Cached constituent files may be used when an NSE live download fails, but this must be recorded as a warning and the cached file must pass the same schema/count validation.

## 6. NSE constituent downloads

NSE constituent CSV endpoints can reject direct HTTP clients. The acquisition layer therefore uses:

1. browser-like HTTP headers
2. an NSE session
3. an initial request to the NSE site to establish session/cookies
4. the same session for the CSV request
5. retries for transient failures
6. validation that the response is actually CSV rather than an HTML block/challenge page
7. a previously cached constituent file as a fallback, when available

A cached fallback is acceptable for resilience, but its use must be visible in dataset diagnostics/provenance.

## 7. Universe validation

All five constituent sources must be present and parse successfully before publishing a new universe snapshot.

Expected source counts:

| Index | Expected |
|---|---:|
| Nifty 50 | 50 |
| Nifty Next 50 | 50 |
| Nifty Midcap 150 | 150 |
| Nifty Smallcap 250 | 250 |
| Nifty Microcap 250 | 250 |
| **Total intended** | **750** |

Duplicates must be reported explicitly. The pipeline must never silently truncate an oversized universe to force a count of 750.

## 8. Publication rule

A failed or incomplete build must never replace the latest known-good analytical dataset.

```text
Build candidate
    ↓
Validate
    ├── FAIL → discard candidate; keep previous dataset
    └── PASS → atomically publish candidate
```

This policy is required for production reliability.
