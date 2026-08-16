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

Phase 0 through Phase 5 are complete. Phase 6 is the next phase.

Phase 5 established:

- Render FastAPI production service
- Vercel Next.js production frontend
- Cloudflare R2 durable shared datasets
- immutable dataset publication
- latest-pointer based activation
- runtime API hydration from R2
- scheduled GitHub Actions data refresh
- production CORS configuration
- automated production smoke test
- real Yahoo/NSE validation
- APCOTEXIND newly-injected-stock test path

## Canonical data contract

NSE 750 = Nifty 50 + Next 50 + Midcap 150 + Smallcap 250 + Microcap 250.

Phase 1 market data is Yahoo Finance Adjusted Close + Volume only, with a 10-year window, common market `as_of`, minimum 126 valid observations and maximum 3-calendar-day freshness.

Do not add High/Low/OHLC silently. Metrics needing those fields require an explicit data-contract decision.

## Responsibility boundaries

```text
NSE/Yahoo acquisition
        ↓
Data validation
        ↓
Quantitative engine
        ↓
Immutable R2 datasets
        ↓
FastAPI query service
        ↓
Next.js UI
```

Frontend never owns financial calculations. User interactions never trigger a full market rebuild.

## Important production configuration

GitHub Actions R2 secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Vercel frontend points to the Render API through its production API environment variable.

Render production CORS must permit the Vercel production origin.

## Validation baseline

The latest production smoke run is green. It checks health, metadata, query, search/sort, export, stock detail, chart ranges, CORS, error handling and frontend availability.

CI also validates real NSE 750/Yahoo data and the frontend production build.

## APCOTEXIND test rule

`APCOTEXIND.NS` is a test stock for the new-constituent path. It must prove that ingestion → validation → metrics → R2 → API → frontend works without special-case code. It must not be permanently injected into the canonical production NSE 750 universe solely for testing.

## Phase 6 objective

Measure the deployed system before changing architecture:

1. Initial frontend load
2. Unfiltered screener query
3. Numeric filter
4. Multi-filter query
5. Sort
6. Search
7. Stock detail
8. Mobile UX
9. Render cold start / R2 bootstrap
10. APCOTEXIND end-to-end path

Capture p50/p95 and optimise only the measured bottleneck.

## Do not do

- Do not modify the old `Pareshking/Umiya` repository.
- Do not reintroduce Streamlit.
- Do not put calculations in the frontend.
- Do not use fake production financial data.
- Do not optimise without measurements.
- Do not add future tabs before Screener quality is established.
- Do not replace the immutable-pointer publication model with ad-hoc mutable files.
