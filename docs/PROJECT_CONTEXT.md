# Umiya Screener V2 — Project Context

**Last updated:** 2026-08-17

This is the first document an AI assistant should read before making a significant change.

## Mission

Build a fast, professional, mobile-first quantitative NSE screener that replaces the old Streamlit interaction model without copying its architecture.

Immediate product scope remains **Screener only**. Other Umiya modules are deferred until the Screener is stable.

## Production

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `/docs`
- Health: `/api/v1/health`

## Current state

Phases 0–4 are complete. Phase 5 production implementation, validation, R2 publication and housekeeping are complete. Phase 5 is formally closed.

Latest validated V2 production data refresh completed successfully on 2026-08-16. The pipeline built the canonical dataset/metrics, validated them, published immutable datasets to R2, advanced the latest pointer and passed production smoke testing.

Latest V2 code changes relevant to momentum data handling:

- `54a451c` — Adjusted Close price cleaning with safe forward-fill after each stock's first genuine observation.
- `ac733c9` — Per-stock available-window momentum weight normalization.
- `c1efbfb8` — Regression test update for the approved forward-fill behaviour.

The corresponding V1 legacy implementation in `Pareshking/Umiya` was also updated by explicit exception on 2026-08-16:

- `b2651179393e7c25e2ff1ba3010c5cd5523ef28a` — full lookback windows and available-window weight normalization.

V1 continues to use **Close**; V2 continues to use **Adjusted Close**. No other V1/V2 momentum systems were intentionally changed by this comparison/fix.

## Architecture

```text
NSE constituent acquisition
        ↓
Yahoo 10Y Adjusted Close + Volume
        ↓
Validation
        ↓
Quantitative metrics
        ↓
Immutable R2 datasets
        ↓
FastAPI on Render
        ↓
Next.js on Vercel
```

Frontend never owns financial calculations. User interactions never trigger a market-wide rebuild.

## Canonical data contract

The canonical universe is based on the NSE index composition used by the project; do not assume a hard-coded 750-row result when the official constituent counts change. The pipeline has dynamic constituent-count validation plus a catastrophic-incompleteness floor.

Phase 1 market data is Yahoo Finance **Adjusted Close + Volume only**, with a 10-year window, common market `as_of`, minimum 126 valid observations and maximum 3-calendar-day freshness. Price and volume freshness are checked independently when both fields are present.

For V2 price matrices, missing observations are **forward-filled after each stock's first genuine observation**. Values before a stock's first observation are never fabricated. This is the validated replacement for the previous no-fill behaviour that caused missing Sharpe/R² components and severe ranking distortion.

No High/Low/OHLC should be added silently. Metrics requiring those fields need an explicit data-contract decision.

Unavailable long-lookback returns remain `NaN`; never manufacture a neutral 0% return for insufficient history.

## Momentum window handling — validated

The primary multi-window momentum system uses matched lookback windows:

| Component | Window |
|---|---:|
| 1M | 21 trading days |
| 3M | 63 trading days |
| 6M | 126 trading days |
| 9M | 189 trading days |
| 12M | 252 trading days |

Each Sharpe/R² component requires its corresponding full window. A stock with insufficient history for a longer horizon is **not assigned a zero for that component**. Instead, available component weights are renormalized for that stock/date.

Primary screener eligibility remains **126 genuine observations**. Therefore a stock with roughly six months of history can rank using its available 1M/3M/6M components without being artificially penalized for unavailable 9M/12M history.

This behaviour was separately audited against the old V1 implementation. The data-processing bug that previously caused hundreds of V2 stocks to lose momentum factors was traced to missing-observation handling, not to a disagreement in the momentum mathematics.

## Hardening completed

- dynamic NSE constituent-count handling
- Yahoo coverage validation
- price/volume freshness validation
- cache TTL/staleness handling
- immutable R2 publication and pointer validation
- safe R2 bootstrap into temporary directories
- corrupt/incomplete dataset rejection
- stale frontend request cancellation
- production smoke tests that do not depend on one hard-coded stock
- regression fixtures aligned with the price+volume eligibility contract
- validated V1/V2 missing-data and momentum-window audit

## R2 / publication

Datasets are immutable. Latest-pointer objects select the active version. Pointer advancement occurs only after successful upload and validation. Failed builds preserve the previous good pointer.

Production GitHub Actions secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

## Phase 5 final housekeeping

Cloudflare R2 lifecycle configuration was manually verified as OK on 2026-08-16:

- historical `datasets/` versions: 30-day retention
- historical `metrics/` versions: 30-day retention
- `pointers/`: protected from the historical expiration rule
- incomplete multipart uploads: 7-day cleanup
- active/latest data remains protected

This is a manual bucket-console verification, not an automated repository assertion.

## APCOTEXIND clarification

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture only. It must not be described as a frontend E2E stock test and must not permanently alter the canonical production universe.

## Phase 6 starting point

After Phase 5 is formally closed, Phase 6 begins with measurement—not redesign:

1. initial frontend load
2. unfiltered query
3. numeric filter
4. multi-filter
5. sort/search
6. stock detail/chart
7. p50/p95 capture
8. mobile UX
9. Render cold start/R2 bootstrap
10. data freshness/as-of verification

Only optimise measured bottlenecks.

## Do not do

- Do not redesign the quantitative methodology without an explicit analysis/decision.
- Do not reintroduce Streamlit.
- Do not put calculations in the frontend.
- Do not use fake production financial data.
- Do not optimise without measurements.
- Do not add future tabs before Screener quality is established.
- Do not replace immutable-pointer publication with ad-hoc mutable files.
- Do not weaken validation just to make CI green.
