# Umiya Screener V2 — Quantitative Methodology

This document is the Phase 2 calculation contract. Every metric here is derivable from the canonical **Adjusted Close + Volume** dataset.

## Lookback convention

Daily observations are counted by valid trading observations, not calendar days. No missing observations are forward-filled.

- 1M = 21 observations
- 3M = 63
- 6M = 126
- 9M = 189
- 12M = 252

## Returns

For lookback `N`, return is:

`(latest valid Adjusted Close / Adjusted Close N observations earlier - 1) × 100`

The latest valid observation is used only after Phase 1 freshness eligibility has been established.

12M Return is explicitly `0` when 252 valid observations are unavailable, per the Phase 1 policy. Other unavailable lookbacks remain missing.

## EMA trend

EMA 50, EMA 100 and EMA 200 are calculated from Adjusted Close with the standard exponential weighting. The latest EMA is compared with the latest valid Adjusted Close.

Outputs:

- EMA value
- price above/below EMA
- percentage distance from EMA

## 52-week proximity

52-week high = maximum Adjusted Close over the most recent 252 observations in the dataset.

`% From 52W High = (CMP / 52W High - 1) × 100`

`Within 20% of 52W High` is true when this value is at least `-20%`.

Because the canonical dataset does not contain High prices, this is a **price-based 52-week high**, not an exchange OHLC high.

## Risk-adjusted momentum

For lookback `N`:

1. Calculate daily log returns.
2. Calculate cumulative log return over `N` observations.
3. Calculate the raw standard deviation of daily log returns over the same `N`-observation window.
4. Normalize the cumulative log return by that same-window volatility and `sqrt(N)`.

This produces the V2 `Sharpe` diagnostic. It is intentionally a defined screening score, not a claim of a textbook annualized portfolio Sharpe ratio.

## Trend quality — R²

For each lookback, regress log Adjusted Close against a linear time index over the full valid window. `R²` is the square of the correlation between log price and time.

R² is unavailable when the complete requested window is not available.

## Momentum score

For each lookback in 1M/3M/6M/9M/12M:

`raw = Sharpe × R²`

The raw cross-section is Z-scored on each market date and clipped to ±3. The configured weights are:

| Lookback | Weight |
|---|---:|
| 1M | 10% |
| 3M | 30% |
| 6M | 30% |
| 9M | 20% |
| 12M | 10% |

Missing components contribute zero; they do not automatically remove an otherwise Phase-1-eligible stock.

## Momentum acceleration

Acceleration compares weighted short-term risk-adjusted momentum with weighted long-term risk-adjusted momentum:

- Short: 10% 1M + 35% 3M + 55% 6M
- Long: 45% 9M + 55% 12M
- Acceleration = short Z-score composite − long Z-score composite

## Persistence

6M persistence = percentage of valid daily log-return observations over the latest 126 observations that are positive.

## Volume ratio

Volume Ratio = latest valid Volume / latest 20-observation average Volume.

Volume is never imputed.

## Industry-relative momentum

Industry Relative = stock Momentum Score − mean Momentum Score of stocks in the same Industry.

## Deliberately excluded in V2 Phase 2

ATR, true range, Chandelier Exit and any other metric requiring High/Low are **not calculated** because High/Low are not part of the canonical data contract.

If these metrics are required later, the data-contract change must be separately approved, documented and tested.

## Integrity requirements

- No look-ahead data.
- No price/volume imputation.
- Deterministic calculations for identical input/configuration.
- Explicit insufficient-history behaviour.
- Symbol alignment preserved.
- Division by zero produces missing values, never fabricated numbers.
- Heavy calculations run in the offline metric build, never during API filtering/sorting.
