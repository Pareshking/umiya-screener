# Umiya Screener V2 — Quantitative Methodology

This document is the calculation contract for the production V2 screener. Metrics are derived offline from the canonical **Adjusted Close + Volume** dataset and served as prepared analytical data.

## Lookback convention

Daily observations are counted on the common market-date grid. The canonical V2 price matrix is forward-filled **only after each stock's first genuine observation**; values before first observation are never fabricated.

- 1M = 21 trading days
- 3M = 63
- 6M = 126
- 9M = 189
- 12M = 252

A metric requiring a full horizon is unavailable when that stock does not have enough genuine history for the requested window.

## Returns

For lookback `N`:

`(latest valid Adjusted Close / Adjusted Close N observations earlier - 1) × 100`

The latest valid observation is used only after Phase 1 freshness/eligibility validation.

Unavailable long-lookback returns remain missing. V2 does not manufacture a neutral 0% return for insufficient history.

## EMA trend

EMA 50, EMA 100 and EMA 200 are calculated from Adjusted Close with standard exponential weighting. The latest Adjusted Close is compared with the latest EMA.

Outputs:

- EMA value
- price above/below EMA
- percentage distance from EMA

## 52-week proximity

52-week high = maximum Adjusted Close over the most recent 252 observations.

`% From 52W High = (CMP / 52W High - 1) × 100`

`Within 20% of 52W High` is true when this value is at least `-20%`.

Because the canonical dataset does not contain High prices, this is a **price-based 52-week high**, not an exchange OHLC high.

## Risk-adjusted momentum

For lookback `N`:

1. Calculate daily log returns.
2. Calculate cumulative log return over the same `N`-observation window.
3. Calculate the raw standard deviation of daily log returns over that same window.
4. Normalize cumulative log return by the same-window volatility and `sqrt(N)`.

This produces the V2 `Sharpe` diagnostic. It is a defined screening score, not a claim of a textbook annualized portfolio Sharpe ratio.

## Momentum score

For each lookback in 1M/3M/6M/9M/12M, use the corresponding **Sharpe** value directly.

The cross-section is Z-scored on each market date and clipped to ±3. Configured weights are:

| Lookback | Weight |
|---|---:|
| 1M | 10% |
| 3M | 30% |
| 6M | 30% |
| 9M | 20% |
| 12M | 10% |

For each stock/date, unavailable horizon components are excluded and the remaining configured weights are renormalized. A Phase-1-eligible stock is therefore not assigned an artificial zero merely because a longer history window is unavailable.

## Momentum acceleration

Acceleration compares weighted short-term risk-adjusted momentum with weighted long-term risk-adjusted momentum:

- Short: 10% 1M + 35% 3M + 55% 6M
- Long: 45% 9M + 55% 12M
- Acceleration = short Z-score composite − long Z-score composite

## Persistence

6M persistence = percentage of valid daily log-return observations over the latest 126 observations that are positive.

## Volume ratio

`Volume Ratio = latest valid Volume / latest 20-observation average Volume`

Volume is never imputed.

## Industry-relative momentum

`Industry Relative = stock Momentum Score − mean Momentum Score of stocks in the same Industry`

## Deliberately excluded in V2

R² is not calculated or exposed in V2. ATR, true range, Chandelier Exit and other metrics requiring High/Low are also not calculated because High/Low are not part of the canonical data contract. Adding those metrics requires an explicit data-contract change.

## Integrity requirements

- No look-ahead data.
- No fabricated pre-listing history.
- Forward-fill is allowed only after first genuine observation in the canonical price matrix.
- Unavailable long horizons remain missing and do not become neutral zeros.
- Available momentum weights are renormalized per stock/date.
- Deterministic calculations for identical input/configuration.
- Explicit insufficient-history behaviour.
- Symbol alignment preserved.
- Division by zero produces missing values.
- Heavy calculations run in the offline metric build, never during API filtering/sorting.
