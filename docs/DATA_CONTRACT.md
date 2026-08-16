# Production Data Contract

## Universe

The canonical universe is based on the NSE index composition used by the project. The pipeline validates constituent coverage dynamically and applies a catastrophic-incompleteness floor; do not assume a permanently fixed row count if official constituent counts change.

## Market data

Yahoo Finance:

- Adjusted Close
- Volume

The canonical historical window is the last 10 years from build date.

## Eligibility

- minimum 126 valid observations
- maximum 3-calendar-day freshness
- common market `as_of` date
- explicit handling of missing/invalid values
- no silent look-ahead

## Missing price observations

For the V2 canonical price matrix, missing observations are forward-filled **after the first genuine observation for each stock**. Values before a stock's first observation are never imputed. This preserves the common market-date grid without fabricating pre-listing history.

## Momentum windows

The primary multi-window momentum system uses matched full lookback windows:

| Horizon | Trading-day window |
|---|---:|
| 1M | 21 |
| 3M | 63 |
| 6M | 126 |
| 9M | 189 |
| 12M | 252 |

Sharpe/R² calculations require the full corresponding window. If a stock does not have enough genuine history for a longer horizon, that component is unavailable rather than assigned a neutral zero. The composite score renormalizes the configured weights over the components actually available for that stock/date.

Primary screener eligibility remains 126 genuine observations.

## Metrics

Metrics are calculated offline and published as prepared analytical data. The API does not calculate the market on demand.

Metric definitions must document inputs, lookback, formula/convention, minimum history and missing-data behaviour.

## Publication

Datasets are versioned and immutable. The active version is selected by a latest-pointer object. Pointer advancement happens only after successful upload and validation.

## Runtime

Render API may hydrate the latest published datasets from R2. Runtime local disk is not the authoritative production store.

## Test fixture rule

`APCOTEXIND.NS` may be used as an opt-in newly-injected-stock test. The fixture must not change the canonical production NSE universe merely to make the frontend show the stock.

## Prohibited changes without explicit review

- Adding OHLC fields because a metric happens to need them.
- Changing the 10-year window silently.
- Changing freshness/eligibility rules silently.
- Changing the canonical universe definition silently.
- Replacing Adjusted Close with unadjusted Close in V2.
- Removing the approved post-first-observation forward-fill behaviour.
- Treating unavailable long-lookback momentum components as zero instead of renormalizing available weights.
- Replacing failed data with hard-coded values.
