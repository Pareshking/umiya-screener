# Phase 8A–8B Production Audit

**Date:** 2026-08-16  
**Status:** In progress

## Audit scope

Initial review covered the production Screener frontend, stock-detail frontend, FastAPI endpoints, query service, data-contract boundaries, and production architecture.

## Finding 8A-01 — stale query response race

### Risk

The Screener fired debounced query requests when filters, search, sort, or page changed, but previous in-flight requests were not cancelled. A slower older response could therefore arrive after a newer response and overwrite the current screen.

This is especially relevant on mobile networks and during rapid search/filter changes.

### Fix

`frontend/app/page.tsx` now creates an `AbortController` for each query effect, passes its signal to `fetch`, aborts the previous request during cleanup, ignores `AbortError`, and prevents aborted requests from changing loading/error/result state.

### Status

**FIXED — awaiting CI/frontend build.**

## Findings reviewed with no defect requiring change

- Stock-detail requests already use `AbortController` for symbol and chart changes.
- Empty query results have an explicit empty state.
- Dataset/API failures have an explicit degraded/error state and retry path.
- Screener pagination is server-side and page size is bounded by the API schema.
- Search uses literal substring matching (`regex=False`), avoiding regex injection behavior.
- Missing metric values remain null/blank rather than being fabricated.
- Chart range is API-bounded (`20..2520` days).
- Stock and chart endpoints reject symbols absent from the current eligible universe.
- R2/metrics data remains backend-driven; frontend does not calculate market-wide metrics.
- Current universe row count is obtained from the dataset rather than forcing 750 rows in the query result.

## Known contract/UX observations for subsequent 8B/8C work

1. The API metadata label `universe_name` is currently a stable product label (`NIFTY 750`) while the actual `universe` count is dynamic. This is acceptable for the product naming convention, but documentation/UI should continue to distinguish product universe name from live constituent count.
2. Frontend filter choices intentionally enumerate the five canonical index families; constituent membership inside those families is data-driven.
3. APCOTEXIND remains a pipeline fixture and must not be promoted into the production universe merely to make a UI test pass.
4. A query with an unsupported sort field currently falls back to `Rank`; this is safe but should be reviewed as an API contract-quality improvement during 8D rather than silently relying on it.

## Next execution

- Run CI and frontend build for 8A-01.
- Continue 8B edge-case tests against the query API: empty results, combined filters, null metrics, pagination boundaries, dynamic universe counts, and newly appearing/missing symbols.
- Then proceed to 8C–8F with the same evidence-first approach.
