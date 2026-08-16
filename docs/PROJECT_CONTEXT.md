# Umiya Screener V2 — Project Context

**Last updated:** 2026-08-16

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

Phases 0–4 are complete. Phase 5 implementation and automated validation are complete. The final Phase 5 housekeeping item is external: verify/configure the actual Cloudflare R2 lifecycle/retention rule.

Latest validated commit before documentation-only changes:
`05cea11ccf2e975e96aea3ff5293384e2d584f27`

Validation result:

- 50 Python tests passed
- frontend build passed
- 10-year Yahoo Adj Close + Volume validation passed
- real current-universe Phase 2 metric validation passed
- production smoke passed

## Architecture

```text
NSE constituent acquisition
        ↓
Yahoo 10Y Adj Close + Volume
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

No High/Low/OHLC should be added silently. Metrics requiring those fields need an explicit data-contract decision.

Unavailable long-lookback returns remain `NaN`; never manufacture a neutral 0% return for insufficient history.

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

## R2 / publication

Datasets are immutable. Latest-pointer objects select the active version. Pointer advancement occurs only after successful upload and validation. Failed builds preserve the previous good pointer.

Production GitHub Actions secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

## Phase 5 final housekeeping

Verify the actual Cloudflare R2 bucket lifecycle configuration:

- historical `datasets/` versions: proposed 30-day retention
- historical `metrics/` versions: proposed 30-day retention
- `pointers/`: never expire through the historical-data rule
- incomplete multipart uploads: proposed 7-day abort rule
- active/latest data must remain protected

Do not mark this complete from repository code alone.

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

- Do not modify the old `Pareshking/Umiya` repository.
- Do not reintroduce Streamlit.
- Do not put calculations in the frontend.
- Do not use fake production financial data.
- Do not optimise without measurements.
- Do not add future tabs before Screener quality is established.
- Do not replace immutable-pointer publication with ad-hoc mutable files.
- Do not weaken validation just to make CI green.
