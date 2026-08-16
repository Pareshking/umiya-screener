# Phase 8A–8B Production Audit

**Date:** 2026-08-16  
**Status:** In progress

## Audit scope

Initial review covered the production Screener frontend, stock-detail frontend, FastAPI endpoints, query service, data-contract boundaries, and production architecture.

## Findings and fixes

### Finding 8A-01 — stale query response race

**Risk:** Debounced Screener requests could overlap. A slower older response could arrive after a newer response and overwrite the current screen, especially on mobile networks and rapid filter/search changes.

**Fix:** `frontend/app/page.tsx` uses a per-query `AbortController`, passes its signal to `fetch`, aborts the previous request during effect cleanup, ignores `AbortError`, and prevents aborted requests from changing loading/error/result state.

**Status:** **FIXED and CI-validated.**

### Finding 8A-02 — request errors were presented as dataset degradation

**Risk:** Any query failure, including a client-side 400 contract error, set the global status to `DEGRADED` and labelled the dataset unavailable.

**Fix:** Frontend now distinguishes API/data unavailability (`503`) from request/contract errors. Only data unavailability enters the degraded state; request failures use a warning/request-failed presentation.

**Status:** **FIXED.**

### Finding 8A-03 — filter search control was non-functional

**Risk:** The mobile filter drawer displayed a search input that did not affect available filter choices.

**Fix:** Filter search is now stateful and filters the canonical index and momentum choices shown in the drawer.

**Status:** **FIXED.**

### Finding 8A-04 — saved screen had no restore path

**Risk:** Save Screen wrote local state but the saved screen was not restored on a later visit.

**Fix:** The existing local save is now restored on initial mount. Malformed local state is ignored safely.

**Status:** **FIXED.**

### Finding 8B-01 — unsupported sort silently fell back to Rank

**Risk:** An invalid sort field could produce a successful response sorted by `Rank`, hiding an API contract error.

**Fix:** Added an explicit `SORTABLE` contract. Unsupported sort fields now raise `ValueError`, mapped by FastAPI to HTTP 400. The response also exposes `available_sorts`.

**Status:** **FIXED and regression-tested.**

### Finding 8B-02 — out-of-range page could return an empty page despite matching rows

**Risk:** A stale page number after filters changed could request a page beyond the new last page and receive no rows even when matches existed.

**Fix:** Query pagination now clamps an out-of-range page to the last available page while preserving the empty-result contract when `total == 0`.

**Status:** **FIXED and regression-tested.**

### Finding 8B-03 — numeric equality did not coerce string values

**Risk:** Numeric filter values supplied as strings could fail exact-match filtering while range operators already coerced numerically.

**Fix:** Numeric `=` filters now use numeric coercion; invalid numeric values still raise a clear validation error.

**Status:** **FIXED and regression-tested.**

## Regression coverage

`tests/test_phase8_edge_cases.py` now covers:

- empty-result pagination;
- combined search/filter/sort/pagination ordering;
- out-of-range page clamping;
- numeric equality coercion;
- unsupported sort contract errors;
- missing numeric values remaining unavailable rather than fabricated.

The validation workflow for the preceding Phase 8 test commit passed on `main`; the new commits are expected to trigger the same validation and production-smoke gates.

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

## Known observations for subsequent 8C–8F work

1. `universe_name` remains the stable product label (`NIFTY 750`) while `universe` is the live eligible constituent count. UI now labels the KPI as the live eligible universe.
2. Frontend filter choices intentionally enumerate the five canonical index families; constituent membership inside those families is data-driven.
3. APCOTEXIND remains a pipeline fixture and must not be promoted into the production universe merely to make a UI test pass.
4. Response payload size, refresh idempotency, last-known-good behavior, R2 lifecycle interaction, and production latency still require the dedicated 8C–8E audit.

## Next execution

1. Validate the new commits through CI/frontend build and production smoke.
2. Complete the 8C data-pipeline resilience audit.
3. Complete 8D API quality/payload review.
4. Measure 8E production/frontend performance and only optimize evidence-backed bottlenecks.
5. Complete 8F documentation/release synchronization.
