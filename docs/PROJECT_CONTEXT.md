# Umiya Screener V2 — Project Context

**Last updated:** 2026-08-17

## Mission

Build a fast, professional, mobile-first quantitative NSE screener that replaces the old Streamlit interaction model without copying its architecture.

The active product scope is **Screener + individual stock research page**. Other Umiya modules remain deferred.

## Production

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `/docs`
- Health: `/api/v1/health`
- Liveness: `/api/v1/live`
- Readiness: `/api/v1/ready`

## Current state

Phases 0–9 are complete. Phase 10 source is complete, with the current R² removal update now under validation before production release.

The production data pipeline, R2 publication, Render API and Vercel architecture remain unchanged except for the prepared metrics contract: R² is no longer calculated or exposed. This update does not redesign the architecture or data publication path.

## Architecture

```text
NSE constituent acquisition
        ↓
Yahoo 10Y Adjusted Close + Volume
        ↓
Validation
        ↓
Offline quantitative metrics
        ↓
Immutable R2 datasets
        ↓
FastAPI on Render
        ↓
Next.js on Vercel
```

The frontend never owns financial calculations. User interactions never trigger a market-wide rebuild.

## Canonical data contract

The canonical universe is based on the NSE index composition used by the project. Constituent coverage is validated dynamically; the official count may legitimately differ from 750.

Production market data is Yahoo Finance **Adjusted Close + Volume** with a 10-year window, common `as_of`, minimum 126 genuine observations and maximum 3-calendar-day freshness.

For V2 price matrices, missing observations are forward-filled **after each stock's first genuine observation**. Values before first observation are never imputed.

## Momentum methodology — validated

Primary windows:

- 1M: 21 trading days
- 3M: 63
- 6M: 126
- 9M: 189
- 12M: 252

Each Sharpe component requires its matching full window. When a longer window is unavailable, that component remains missing and the configured momentum weights are renormalized over the components available for that stock/date.

Primary screener eligibility remains 126 genuine observations.

V2 uses Adjusted Close. R² is deliberately removed from the momentum score and stock-research output; the momentum score is based on the weighted cross-sectional Z-score of Sharpe across the five lookbacks.

## Phase 10 result

The final UI is intentionally table-first and compact:

- no persistent desktop sidebar;
- no oversized dashboard/status cards;
- structured filter drawer;
- active filter chips and Clear all;
- debounced/cancellable server-side search;
- explicit X/Clear search control;
- dense sortable table with sticky headers;
- responsive mobile result cards;
- compact stock header;
- chart-led stock research page;
- dedicated Momentum, Risk & Trend, and Relative/Data Context sections;
- duplicate metric representations removed.

## Production safety

- no fabricated production financial data;
- no frontend market-wide calculations;
- immutable R2 publication with latest pointers;
- failed builds preserve the previous good pointer;
- ATR/High/Low-dependent metrics remain excluded because OHLC is not in the data contract.

## APCOTEXIND clarification

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture only. It must not be described as a frontend E2E stock test or permanently added to the canonical production universe.

## Final state

Phase 10 UI engineering is complete. The current R²-removal change is a quantitative-contract maintenance loop on `main`; it must pass the existing Python, frontend and production validation gates before being treated as production-ready.
