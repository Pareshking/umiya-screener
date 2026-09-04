# Umiya Screener V2 — Quantitative Methodology

Phase 2 is the analytical contract between the canonical Phase 1 dataset and the API.

## Canonical inputs

- `adj_close`: Yahoo Finance Adjusted Close only
- `volume`: Yahoo Finance Volume only
- 5 NSE constituent sets, preserving index membership
- Minimum eligible history: 126 valid observations
- Common market `as_of` date and maximum 3-calendar-day freshness are enforced by Phase 1

No metric is allowed to fetch market data or rebuild the dataset at query time.

Dates on which more than 70% of the universe has no observation are dropped before any metric is computed: those rows are market holidays that leaked into the vendor's date grid, and keeping them drags every cross-sectional statistic on that date towards the handful of symbols that did print.

## Lookbacks

Horizons are **calendar periods, not fixed trading-row counts**.

| Label | Calendar period | Weight |
|---|---:|---:|
| 1M | 1 month | 10% |
| 3M | 3 months | 30% |
| 6M | 6 months | 30% |
| 9M | 9 months | 20% |
| 12M | 12 months | 10% |

Earlier versions read "1M" as the last 21 rows and "12M" as the last 252 rows. NSE trades a variable number of sessions per month, and every holed session shifts a row-counted window a day further back, so a "12M return" could silently span 11 or 13 months depending on how complete the vendor data happened to be. The window is now defined by dates:

- The **as-of date** is today's India date for genuinely current data, or the dataset's last observation when the dataset is more than 7 days stale. A stale or offline dataset therefore cannot acquire a synthetic multi-year lookback.
- The **target start** is `as_of - DateOffset(months=N)`.
- The window **opens on the first available market date on or after the target**.
- If that opening observation is more than 7 calendar days after the target, the dataset does not reach back that far and the horizon stays unavailable. A 12M label is never attached to a shorter window.

The opening price may be carried forward by at most 5 sessions (one trading week) to bridge holes the vendor leaves. A stock with no print for longer than that scores unavailable rather than anchoring on a stale price.

See `src/calendar_momentum.py`.

## Returns

`ROC_N = (P_end / P_start - 1) * 100`, where `P_start` is the observation the calendar window opens on and `P_end` is the latest observation.

Nothing is interpolated, and no value is fabricated when a horizon is unreachable: an unavailable lookback is reported as missing, not as zero.

## Risk-adjusted momentum / Sharpe

For a calendar window of `N` months spanning `n` observations:

1. `daily_log_return = ln(P_t / P_(t-1))`
2. `cumulative_log_return = ln(P_end / P_start)`
3. `period_volatility = population_std(daily_log_return over the window) * sqrt(n)`
4. `risk_adjusted_return = cumulative_log_return / period_volatility`

Only the economic horizon and the observation count `n` are calendar-defined; the period-scale volatility math is unchanged from the legacy engine. It is intentionally not replaced by a textbook risk-free-rate Sharpe implementation.

R² (the squared correlation between log price and a time index) was previously multiplied into this score. It has been removed: it is not part of the current contract and must not be reintroduced without an explicit decision.

## Composite momentum score

For each lookback:

- calculate `risk_adjusted_return` over the calendar window
- **winsorise** the date's cross-section at ±3σ, then cross-sectionally standardize it, then clamp the result to `[-3, +3]`
- combine using the weights above

Winsorising before standardizing keeps a single extreme name from stretching the mean and standard deviation that every other name is scored against. A cross-section needs at least 3 real observations and non-zero spread to be scored at all; below that the date is unavailable.

Stocks with less than 126 valid observations are ineligible. Components a stock cannot yet support are **omitted and the remaining weights renormalized for that stock**, so a recent listing is not penalised merely for lacking 9M/12M history.

## Trend

Calculated from Adjusted Close:

- EMA 50 / 100 / 200
- `% distance from EMA = (CMP / EMA - 1) * 100`
- 52-week high = maximum Adjusted Close over the trailing **12 calendar months**
- `% from 52W high = CMP / 52W High - 1`
- `Within 20% of 52W High` when the distance is at least -20%

## Persistence

`Persistence 6M %` = positive daily log-return observations / valid daily log-return observations over the trailing **6 calendar months** × 100.

This is the frog-in-the-pan measure: how steadily a move was delivered, rather than how large it was.

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
