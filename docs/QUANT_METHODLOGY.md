# Umiya Screener V2 — Quantitative Methodology

This document is the calculation contract for the production V2 screener. Metrics are derived offline from the canonical **Adjusted Close + Volume** dataset and served as prepared analytical data.

## Lookback convention

Horizons are **calendar periods**, not fixed trading-day counts:

- 1M = 1 calendar month
- 3M = 3 calendar months
- 6M = 6 calendar months
- 9M = 9 calendar months
- 12M = 12 calendar months

For each observation date the window's start target is that date minus the requested number of calendar months, and the window opens on the first available market date on or after that target. NSE trades a variable number of sessions per month, so a fixed 21/63/126/189/252-row window drifts against the calendar and silently changes the economic horizon it reports.

The as-of date is today's India date when the dataset is current, and the dataset's own last observation when it is more than 7 days stale, so an offline dataset cannot acquire a synthetic lookback.

A horizon is unavailable when the dataset does not reach back to its target start (more than 7 calendar days short), or when the stock has no usable price at either end of the window. The window's opening price may be bridged across at most 5 sessions of missing data; beyond that the horizon is missing rather than anchored on a stale price.

The canonical V2 price matrix is gap-bridged **only after each stock's first genuine observation** and only for up to 5 sessions; values before first observation are never fabricated, and a suspended stock is not carried forward indefinitely.

Dates where more than 70% of the universe has no observation are dropped as market holidays before any metric is computed.

See `src/calendar_momentum.py`.

## Returns

For a lookback of `N` calendar months:

`(latest valid Adjusted Close / Adjusted Close at the window's opening market date - 1) × 100`

The latest valid observation is used only after Phase 1 freshness/eligibility validation.

Unavailable long-lookback returns remain missing. V2 does not manufacture a neutral 0% return for insufficient history.

## EMA trend

EMA 50, EMA 100 and EMA 200 are calculated from Adjusted Close with standard exponential weighting. The latest Adjusted Close is compared with the latest EMA.

Outputs:

- EMA value
- price above/below EMA
- percentage distance from EMA

## 52-week proximity

52-week high = maximum Adjusted Close over the trailing 12 calendar months.

`% From 52W High = (CMP / 52W High - 1) × 100`

`Within 20% of 52W High` is true when this value is at least `-20%`.

Because the canonical dataset does not contain High prices, this is a **price-based 52-week high**, not an exchange OHLC high.

## Risk-adjusted momentum

For a lookback of `N` calendar months spanning `n` observations:

1. Calculate daily log returns.
2. Calculate cumulative log return from the window's opening price to the latest price.
3. Calculate the population standard deviation of daily log returns over that same window.
4. Normalize cumulative log return by the same-window volatility scaled by `sqrt(n)`.

This produces the V2 `Sharpe` diagnostic. It is a defined screening score, not a claim of a textbook annualized portfolio Sharpe ratio.

## Momentum score

For each lookback in 1M/3M/6M/9M/12M, use the corresponding **Sharpe** value directly.

On each market date the cross-section is **winsorised at ±3σ, then Z-scored, then clamped to ±3**. Winsorising first stops a single extreme name from stretching the mean and standard deviation every other name is measured against. A date needs at least 3 real observations and non-zero spread to be scored. Configured weights are:

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

6M persistence = percentage of valid daily log-return observations over the trailing 6 calendar months that are positive. This is the frog-in-the-pan measure of how steadily a move was delivered.

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
- Forward-fill is allowed only after first genuine observation in the canonical price matrix, and only for up to 5 sessions.
- Horizons are calendar-defined; a longer label is never attached to a shorter window.
- Unavailable long horizons remain missing and do not become neutral zeros.
- Available momentum weights are renormalized per stock/date.
- Deterministic calculations for identical input/configuration.
- Explicit insufficient-history behaviour.
- Symbol alignment preserved.
- Division by zero produces missing values.
- Heavy calculations run in the offline metric build, never during API filtering/sorting.
