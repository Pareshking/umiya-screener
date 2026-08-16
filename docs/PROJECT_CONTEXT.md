# Umiya Screener V2 — Project Context

**Last updated:** 2026-08-16

This file is the first document an AI assistant should read before making a significant change.

## Mission

Build a fast, professional, mobile-first quantitative NSE screener that replaces the old Streamlit interaction model without copying its architecture.

Immediate product scope remains **Screener only**. Other Umiya modules are deferred until the Screener is stable.

## Production endpoints

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `/docs`
- Health: `/api/v1/health`

## Current state

Phase 0 through Phase 4 are complete. Phase 5 implementation and production integration are complete. **Phase 5 has exactly one remaining housekeeping item: verify/configure the Cloudflare R2 object lifecycle/retention policy. Phase 6 has not formally started.**

There is currently an open Phase 5 production-integration PR (#18); do not interpret the documentation as permission to skip that review/merge process.

## Phase 5 final housekeeping

The only remaining Phase 5 gate is:

- Verify the R2 bucket has a lifecycle rule that prevents indefinite accumulation of old immutable dataset versions.
- The rule should target historical immutable data under `datasets/` and `metrics/`.
- Do not expire `pointers/` through the historical-data rule; latest pointers must remain available.
- Verify the active/latest dataset is never deleted while it is current.

A reasonable initial retention target is **30 days** for immutable historical datasets, subject to the user's final rollback/retention preference. This should be configured at the R2 bucket level, not simulated in application code.

The repository contains no lifecycle configuration that proves the external R2 bucket is configured. Do not mark this item complete without verifying the actual bucket configuration.

## APCOTEXIND clarification

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture only. **It was never intended to be shown in the production frontend and must not be described as a frontend end-to-end stock test.** It must not permanently alter the canonical NSE 750 universe merely to make the stock appear in the UI.

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

NSE 750 = Nifty 50 + Next 50 + Midcap 150 + Smallcap 250 + Microcap 250.

Phase 1 market data is Yahoo Finance Adjusted Close + Volume only, with a 10-year window, common market `as_of`, minimum 126 valid observations and maximum 3-calendar-day freshness.

Do not add High/Low/OHLC silently. Metrics needing those fields require an explicit data-contract decision.

## R2 / publication

Datasets are immutable. Latest-pointer objects select the active version. Pointer advancement occurs only after successful upload and validation. Failed builds preserve the previous good pointer.

Production GitHub Actions secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

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

Only optimise a measured bottleneck.

## Do not do

- Do not modify the old `Pareshking/Umiya` repository.
- Do not reintroduce Streamlit.
- Do not put calculations in the frontend.
- Do not use fake production financial data.
- Do not optimise without measurements.
- Do not add future tabs before Screener quality is established.
- Do not replace the immutable-pointer publication model with ad-hoc mutable files.
