# Production Data Contract

## Universe

Exactly 750 unique NSE symbols from:

- Nifty 50
- Nifty Next 50
- Nifty Midcap 150
- Nifty Smallcap 250
- Nifty Microcap 250

Index membership is retained.

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

## Metrics

Metrics are calculated offline and published as prepared analytical data. The API does not calculate the market on demand.

Metric definitions must document inputs, lookback, formula/convention, minimum history and missing-data behaviour.

## Publication

Datasets are versioned and immutable. The active version is selected by a latest-pointer object. Pointer advancement happens only after successful upload and validation.

## Runtime

Render API may hydrate the latest published datasets from R2. Runtime local disk is not the authoritative production store.

## Test fixture rule

`APCOTEXIND.NS` may be used as an opt-in newly-injected-stock test. The fixture must not change the canonical production NSE 750 membership merely to make the frontend show the stock.

## Prohibited changes without explicit review

- Adding OHLC fields because a metric happens to need them.
- Changing the 10-year window silently.
- Changing freshness/eligibility rules silently.
- Changing the canonical 750-universe definition silently.
- Replacing Adj Close with unadjusted Close.
- Replacing failed data with hard-coded values.
