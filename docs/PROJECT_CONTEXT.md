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

For V2 price matrices, missing observations are forward-filled **after each stock's first genuine observation**, and only across gaps of at most 5 sessions. Values before first observation are never imputed, and a suspended stock is not carried forward indefinitely. Dates where more than 70% of the universe has no observation are dropped as market holidays.

## Momentum methodology — validated

Primary horizons are **calendar periods**, not fixed trading-day counts:

- 1M: 1 calendar month
- 3M: 3 calendar months
- 6M: 6 calendar months
- 9M: 9 calendar months
- 12M: 12 calendar months

Each window opens on the first market date on or after `as_of - N months`. A row-counted window drifts against the calendar — NSE trades a variable number of sessions per month — so the labelled horizon and the measured horizon diverge. See `src/calendar_momentum.py`.

Each Sharpe component requires its window to actually reach its calendar target (within 7 days). When a longer horizon is unavailable, that component remains missing and the configured momentum weights are renormalized over the components available for that stock/date.

Primary screener eligibility remains 126 genuine observations.

V2 uses Adjusted Close. R² is deliberately removed from the momentum score and stock-research output; the momentum score is based on the weighted, winsorised cross-sectional Z-score of period-scale Sharpe across the five calendar lookbacks.

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
