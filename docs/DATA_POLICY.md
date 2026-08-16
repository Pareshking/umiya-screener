# Umiya V2 — Data Quality & Missing-Data Policy

This document is part of the V2 source of truth. It defines the canonical market-data contract, exchange-calendar handling, partial stock history, freshness, and NSE constituent downloads.

## 1. Canonical market-data contract

The production V2 price dataset contains only:

- **Adjusted Close** from Yahoo Finance
- **Volume** from Yahoo Finance

The historical window is the **last 10 years from the date of the data build**. We do not download Yahoo's full history back to the earliest available date.

Open, High, Low and unadjusted Close are not part of the canonical dataset. If a future quantitative metric genuinely requires another field, that is an explicit methodology decision and must be documented and tested before changing the contract.

## 2. Exchange holidays and weekends

Weekends and exchange holidays are **not missing observations**. They normally do not appear as rows in daily price/volume data and must not cause a data-quality failure.

Do not manufacture Saturday/Sunday/holiday rows merely to make the index continuous.

The screener uses **one common market as-of date**: the latest valid trading date present in the downloaded universe. We do not let each stock choose a different market date.

## 3. Missing observations for individual stocks

A missing price or volume observation for one stock must **not delete the trading-date row for the rest of the universe**.

Historical gaps and trailing gaps remain missing. **V2 does not forward-fill or otherwise impute market prices/volume.**

A stock may still be eligible when its latest valid observation is behind the common market date, provided it passes the explicit freshness limit. The dataset records that age rather than fabricating an observation.

## 4. Minimum stock history

A stock is eligible for the Screener when it has at least **126 valid daily Adjusted Close observations** and at least 126 valid Volume observations.

A stock with fewer than 126 valid observations is excluded from Screener ranking/results, but its short history must not cause the entire pipeline to fail.

The minimum-history rule is about valid observations, not calendar days.

## 5. Data freshness

Every eligible stock must also have a latest valid Adjusted Close observation no more than **3 calendar days behind the common market as-of date**.

This is deliberately checked separately from the 126-observation rule.

Examples:

- Market as-of Friday; stock last traded Friday → age 0 → eligible.
- Market as-of Friday; stock last traded Thursday → age 1 → eligible.
- Market as-of Friday; stock last traded Tuesday → age 3 → eligible.
- Market as-of Friday; stock last traded Monday → age 4 → **not eligible**.

A weekend or exchange holiday does not create a fake missing trading row. The common market as-of date remains the latest actual trading date.

This prevents the incorrect behaviour of simply taking each stock's own latest price and treating it as though it represents the same market date as every other stock.

## 6. Longer lookbacks

Having only 126 valid observations does **not** make a stock unusable.

Longer metrics may be unavailable for newer stocks. Missing longer-lookback components must not disqualify an otherwise eligible stock.

Current policy:

- 1M and 3M use available valid history when sufficient observations exist.
- 6M is available with 126 valid observations.
- 9M may be unavailable when sufficient history does not exist.
- **12M RoC is explicitly defined as 0 when a full 12M history is unavailable.**
- Missing components of the weighted momentum score contribute zero rather than removing the eligible stock.

Any future change must be an explicit methodology decision, not an accidental implementation consequence.

## 7. No silent data fabrication

Prohibited:

- fabricating prices
- arbitrary missing-price replacement
- forward-filling prices or volume
- silently treating an old stock price as current when it is outside the 3-day freshness limit
- using each stock's own later date as the screener's market date
- treating a missing 12M return as a positive/negative estimate
- silently substituting unrelated symbols
- silently replacing failed live market data with fake values

Freshness is a qualification rule, not permission to manufacture a current observation.

## 8. NSE constituent downloads

NSE constituent CSV endpoints can reject direct HTTP clients. The acquisition layer therefore uses:

1. browser-like HTTP headers
2. an NSE session
3. an initial request to the NSE site to establish session/cookies
4. the same session for the CSV request
5. retries for transient failures
6. validation that the response is actually CSV rather than an HTML block/challenge page
7. a previously cached constituent file as a fallback, when available

A cached fallback is acceptable for resilience, but its use must be visible in dataset diagnostics/provenance.

## 9. Universe validation

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

Duplicates must be reported explicitly. The Phase 1 build requires exactly 750 unique symbols; it must never silently truncate an oversized universe to force a count of 750.

## 10. Publication rule

A failed or incomplete build must never replace the latest known-good analytical dataset.

```text
Build candidate
    ↓
Validate
    ├── FAIL → discard candidate; keep previous dataset
    └── PASS → atomically publish candidate + update LATEST pointer
```

This policy is required for production reliability.
