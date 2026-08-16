# Phase 8A–8E Production Audit

**Date:** 2026-08-16  
**Status:** **Complete**

## Audit scope

Production Screener frontend, stock-detail frontend, FastAPI endpoints, query service, data-contract boundaries, storage publication path, and production architecture.

## 8A — UX findings and fixes

- **8A-01 stale query response race:** fixed with per-query `AbortController` cancellation and CI validation.
- **8A-02 degraded-state conflation:** fixed; HTTP 503/data unavailability is separated from ordinary request/contract errors.
- **8A-03 mobile filter search:** fixed and made stateful.
- **8A-04 saved-screen restore:** fixed with safe initial-state restoration and malformed-state handling.

Repository-level loading, error, cancellation and chart paths were reviewed. A human visual walkthrough on a real browser/device remains an explicitly external observation and is not claimed as automated evidence.

## 8B — Correctness findings and fixes

- Unsupported sort fields now return HTTP 400 instead of silently falling back to Rank.
- Out-of-range pages clamp to the last page when matches exist; true empty results retain `pages=1, rows=[]`.
- Numeric equality filters coerce numeric strings consistently.
- Null/missing metrics remain unavailable rather than fabricated.
- Dynamic universe membership is data-driven rather than hard-coded to 750.

Regression coverage includes empty results, combined query ordering, pagination boundaries, numeric coercion, invalid sort and missing values.

## 8C — Data pipeline resilience

R2 pointer targets are validated for absolute paths, traversal and namespace violations before hydration. Immutable local publication uses temporary candidate directories followed by atomic rename; latest pointers advance only after successful publication; remote downloads are validated before activation; last-known-good metrics remain available on sync failure; catastrophic universe collapse is rejected; duplicates are recorded/deduplicated.

New Phase 8 regression coverage explicitly verifies:

- repeated successful refreshes produce separate valid immutable datasets and advance `LATEST.json` safely;
- constituent replacement produces a new dataset containing the new member without mutating the previous dataset or retaining the removed member.

Existing controlled production refresh evidence confirms the R2 publication/readiness path. Lifecycle policy remains `datasets/` and `metrics/` 30-day historical retention, protected `pointers/`, and 7-day incomplete multipart cleanup.

## 8D — API quality

Request IDs, `Cache-Control: no-store`, bounded query/search/request sizes, explicit filter/sort errors, null preservation and production payload measurements are verified.

Latest production smoke:

- query timings: 247, 290, 120, 86, 83 ms;
- query p50: **120 ms**;
- query p95: **247 ms**;
- query payload: **11,916 B**;
- search-sort: **1,882 B**;
- stock detail: **1,119 B**;
- charts: **4,902 / 9,852 / 19,627 B**;
- export: **387,796 B**;
- invalid filter/sort: **HTTP 400**;
- overall production smoke: **PASS**.

No payload optimization was introduced because the measurements do not establish a concrete bottleneck.

## 8E — Performance/frontend polish

Repeated production latency remains within the measured Phase 6/8 evidence baseline. No unmeasured optimization was introduced. Repository-level frontend behavior and API cancellation/error paths were reviewed.

## Production deployment note

The frontend deployment platform had reported a temporary Vercel deployment rate-limit on the latest frontend-changing checkpoint. This is external deployment capacity, not a source-code test failure. The deployed Render API production smoke passed.

## Regression coverage

- `tests/test_phase8_edge_cases.py` — query correctness/edge cases.
- `tests/test_storage.py` — R2 pointer namespace/traversal validation.
- `tests/test_phase8_pipeline.py` — repeated refresh/idempotency and constituent replacement scenarios.
- Existing `tests/test_injected_stock_flow.py` — newly appearing constituent/APCOTEXIND pipeline fixture behavior.

## Constraints preserved

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains canonical.
- Live universe is not hard-coded to exactly 750.
- `APCOTEXIND.NS` remains a pipeline fixture and is not promoted to production.
- Quantitative methodology is unchanged.
- No optimization without measurement.
