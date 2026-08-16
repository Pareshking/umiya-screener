# Umiya Screener V2 — Quantitative Methodology

Phase 2 is the analytical contract between the canonical Phase 1 dataset and the API.

## Canonical inputs

- `adj_close`: Yahoo Finance Adjusted Close only
- `volume`: Yahoo Finance Volume only
- 5 NSE constituent sets, preserving index membership
- Minimum eligible history: 126 valid observations
- Common market `as_of` date and maximum 3-calendar-day freshness are enforced by Phase 1

No metric is allowed to fetch market data or rebuild the dataset at query time.

## Lookbacks

| Label | Days | Weight |
|---|---:|---:|
| 1M | 21 | 10% |
| 3M | 63 | 30% |
| 6M | 126 | 30% |
| 9M | 189 | 20% |
| 12M | 252 | 10% |

## Returns

`ROC_w = (P_t / P_(t-w) - 1) * 100` using each symbol's own valid observations.

No forward-fill or interpolation is performed. If a symbol has insufficient observations for a lookback, that lookback remains unavailable. Per the V2 decision, **12M ROC is explicitly 0 when unavailable**; this does not fabricate a price observation.

## Risk-adjusted momentum / Sharpe

For window `w`:

1. `daily_log_return = ln(P_t / P_(t-1))`
2. `cumulative_log_return = ln(P_t / P_(t-w))`
3. `annualized_volatility = rolling_std(daily_log_return, w) * sqrt(w)`
4. `risk_adjusted_return = cumulative_log_return / annualized_volatility`
5. Momentum quality = `risk_adjusted_return * R²`

`R²` is the squared Pearson correlation between log price and a linear time index over the same window.

This is the methodology used by the legacy Umiya momentum engine and is retained for V2 parity. It is intentionally not replaced by a textbook risk-free-rate Sharpe implementation.

## Composite momentum score

For each lookback:

- calculate `risk_adjusted_return * R²`
- cross-sectionally standardize across the universe
- clip the resulting Z-score to `[-3, +3]`
- combine using the weights above

Stocks with less than 126 valid observations are ineligible. Missing long-window components are not imputed with prices; the composite treats an unavailable component as zero contribution, while the explicit 12M ROC display fallback remains zero.

## Trend

Calculated from Adjusted Close:

- EMA 50 / 100 / 200
- `% distance from EMA = (CMP / EMA - 1) * 100`
- 52-week high = maximum Adjusted Close over the latest 252 observations
- `% from 52W high = CMP / 52W High - 1`
- `Within 20% of 52W High` when the distance is at least -20%

## Persistence

`Persistence 6M %` = positive daily log-return observations / valid daily log-return observations over the latest 126 observations × 100.

## Volume

`Volume Ratio = latest valid volume / 20-observation average volume`.

## Industry relative strength

`Industry Relative = stock Momentum Score - mean Momentum Score of its industry group`.

Missing industry is mapped to `Other`.

## Momentum acceleration

`Short = 0.10*Z(1M) + 0.35*Z(3M) + 0.55*Z(6M)`

`Long = 0.45*Z(9M) + 0.55*Z(12M)`

`Acceleration = Short - Long`.

## Deliberately excluded from Phase 2

ATR, ATR%, Chandelier stops and other OHLC-derived indicators are **not implemented** because the canonical V2 contract contains no High/Low fields. Adding them requires an explicit data-contract decision rather than silently changing the Phase 1 dataset.

Residual market alpha and market-cap weighting are also not part of the current Screener V2 contract because no canonical benchmark/market-cap dataset was selected.

## Integrity requirements

Every metric must be deterministic, symbol-aligned, look-ahead safe, network-free, and independently testable. Synthetic/reference tests are mandatory for formula changes.
