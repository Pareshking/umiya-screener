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

- 1M, 3M, 6M and 9M returns are available only when their required observation window exists.
- **12M Return remains unavailable (NaN) when 12M history is insufficient. It is never converted to a neutral 0% return.**
- Missing components of the weighted momentum score contribute zero rather than removing the eligible stock.

Any future change must be an explicit methodology decision, not an accidental implementation consequence.

## 7. No silent data fabrication

Prohibited:

- fabricating prices
- arbitrary missing-price replacement
- forward-filling prices or volume
- silently treating an old stock price as current when it is outside the 3-day freshness limit
- using each stock's own later date as the screener's market date
- treating a missing long-lookback return as a neutral estimate
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

## 9. NSE universe validation and dynamic constituent counts

The five official constituent files are the **source of truth for current membership**. The nominal index sizes are reference/baseline counts, not a requirement that the software always produce exactly those numbers.

Current baselines:

| Index | Baseline |
|---|---:|
| Nifty 50 | 50 |
| Nifty Next 50 | 50 |
| Nifty Midcap 150 | 150 |
| Nifty Smallcap 250 | 250 |
| Nifty Microcap 250 | 250 |
| **Nominal combined universe** | **750** |

Legitimate changes in security count must be accepted and recorded as a warning. For example, NSE's methodology allows an additional security such as a DVR to make the security count differ from the nominal company count. The system therefore does **not** truncate an oversized universe or fail merely because a source has 51 instead of 50 securities.

At the same time, the pipeline protects against malformed/truncated downloads. Each source must contain at least 80% of its normal baseline count. A source below that floor is treated as a structural/source failure and the build is rejected rather than publishing an incomplete universe.

Duplicates across the five source files are reported explicitly and deduplicated by symbol for the canonical combined universe.

The final combined universe must contain at least **80% of the nominal combined baseline (600 unique symbols)**. The actual unique count is recorded in dataset metadata and may differ from 750.

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

## Third-party fundamentals: added 2026-09-05, removed 2026-09-06

Fundamentals, delivery data and NSE sector classification were briefly joined
from a third-party GitHub repository. They have been removed entirely. This
section records why, so the decision is not quietly revisited.

### What the source was

A public repo publishing a static site, whose `m.json` was a PHPMyAdmin export
of a private MySQL database, committed once per trading day. Not a pipeline:
the code producing the numbers was not in the repo, so they could not be
reproduced, audited or repaired. It carried no licence.

### Why it was removed

Its valuation ratios were computed against a **stale price** while the same row
published a current close. Verified against an independent source for WELCORP
on 2026-09-04 (close Rs 2,590.60): a single factor of 1.623 carried its P/E
18.23 to the true 29.59, its price-to-book 4.60 to 7.46, and — dividing,
because price sits in the denominator — its yield 0.31% to 0.19%. One stale
price numerator explained all three. The implied price of ~Rs 1,596 was
confirmed independently across seven peers, agreeing to the rupee on two.

Staleness ranged 4%–38%, tracking how far each stock had run. **This is a
momentum screener**: it surfaces the stocks that have risen most, which are
exactly the stocks whose P/E was understated most. WELCORP ranked #1 while
showing a P/E of 18 against a real 30 — the biggest winners looked cheapest,
and the error grew with the very thing the ranking selects for.

The quarterly growth figures failed separately: no pairing of the independent
source's own quarterly results reproduced the reported -55% EPS or -14% sales.
Debt did not reconcile with debt-to-equity either.

Market cap, shareholding and the close price did reconcile exactly. But a
source that is wrong on valuation and growth, cannot be audited, and cannot be
repaired from what it publishes is not a foundation to build on, so the whole
dependency was dropped rather than partially trusted.

### What the screener uses now

Only the canonical Adjusted Close + Volume dataset the project controls end to
end. Every number on the site is computed from it. There is no third-party
data in the product.

### If fundamentals are wanted again

Take them from a source whose figures can be reconciled, and reconcile them on
every build rather than once. Most of what was being consumed — sector
classification, delivery volumes, shareholding — is published by NSE directly
and is reproducible from its own files.
