# Phase 8A–8E Production Audit

**Date:** 2026-08-16  
**Status:** In progress

## Audit scope

The audit covers the production Screener frontend, stock-detail frontend, FastAPI endpoints, query service, data-contract boundaries, storage publication path, and production architecture.

## 8A — UX findings and fixes

### 8A-01 — stale query response race

**Fix:** `frontend/app/page.tsx` uses a per-query `AbortController`, aborts the previous request during effect cleanup, ignores `AbortError`, and prevents aborted requests from changing loading/error/result state.

**Status:** **FIXED and CI-validated.**

### 8A-02 — request errors were presented as dataset degradation

**Fix:** Frontend now distinguishes API/data unavailability (`503`) from request/contract errors. Only data unavailability enters the degraded state; ordinary request failures use a warning presentation.

**Status:** **FIXED.**

### 8A-03 — filter search control was non-functional

**Fix:** Mobile filter search is now stateful and filters the available canonical choices.

**Status:** **FIXED.**

### 8A-04 — saved screen had no restore path

**Fix:** Existing saved-screen state is restored on initial mount; malformed local state is ignored safely.

**Status:** **FIXED.**

## 8B — correctness findings and fixes

### 8B-01 — unsupported sort silently fell back to Rank

**Fix:** Added an explicit `SORTABLE` contract. Unsupported sort fields return HTTP 400 and `available_sorts` is exposed by the query response.

**Status:** **FIXED and regression-tested. Production smoke also verifies the 400 contract.**

### 8B-02 — out-of-range page could return an empty page despite matching rows

**Fix:** Query pagination clamps an out-of-range page to the last available page when matches exist while preserving `pages=1, rows=[]` for a true empty result.

**Status:** **FIXED and regression-tested.**

### 8B-03 — numeric equality did not coerce string values

**Fix:** Numeric `=` filters now coerce numeric strings consistently.

**Status:** **FIXED and regression-tested.**

## 8C — data pipeline resilience review

### 8C-01 — R2 pointer targets were not explicitly validated before hydration

**Risk:** Pointer contents are remote data and must not be treated as trusted filesystem-like paths.

**Fix:** Added `validate_pointer_prefix()` and applied it before object-store prefix download. Absolute paths, traversal components and namespace mismatches are rejected by the helper; downloaded object keys continue to receive destination-path containment checks.

**Status:** **FIXED and regression-tested.**

### Existing resilience verified

- Immutable local dataset publication uses temporary candidate directories followed by atomic rename.
- Latest local pointers are updated only after a successful candidate publication.
- Remote downloads are performed into temporary directories and validated before replacing active local datasets.
- Empty remote prefixes are rejected.
- Malformed pointers are rejected.
- Last-known-good metric cache remains available when remote synchronization fails.
- Current-universe construction is data-driven and catastrophic coverage collapse is rejected.
- Duplicate constituent symbols are recorded and deduplicated rather than silently creating duplicate rows.
- Production R2 lifecycle was already verified: datasets/metrics historical versions 30 days, pointers protected, incomplete multipart uploads 7 days.

### Remaining 8C evidence gate

- Explicit repeat-refresh/idempotency run is still a planned validation item.
- A fresh controlled production refresh after the latest pointer-validation code change should be used as the final live R2 confirmation.

## 8D — API quality

### Completed

- Request IDs and `Cache-Control: no-store` are already enforced by the operational middleware.
- Query page size is bounded to 200 by the API schema.
- Search length is bounded to 80 characters.
- Request bodies are capped by production middleware.
- Filter and sort contract failures map to HTTP 400.
- Missing metric values remain null rather than fabricated.
- Production smoke now records response payload sizes for metadata, query/search, stock detail, charts and export.
- Production smoke explicitly verifies the unsupported-sort HTTP 400 contract.

### Remaining evidence gate

No payload-size optimization will be made without measured evidence from the production smoke output.

## 8E — performance/frontend polish

The existing production smoke already records five query timings and reports p50/p95. The latest production-smoke workflow completed successfully after adding payload-size measurements and the bad-sort contract check.

No optimization has been introduced without evidence.

The remaining observation that cannot be automated by repository tooling is an independent human desktop/mobile visual walkthrough of the deployed Next.js UI.

## Production deployment note

The latest repository code is validated through GitHub workflows. Vercel has currently reported a deployment rate-limit status (`Deployment rate limited — retry in 24 hours`) for the latest frontend-changing checkpoint. This is an external deployment-capacity limitation, not a source-code test failure. Render/API production smoke continues to pass against the deployed API.

## Regression coverage

`tests/test_phase8_edge_cases.py` covers:

- empty-result pagination;
- combined search/filter/sort/pagination ordering;
- out-of-range page clamping;
- numeric equality coercion;
- unsupported sort contract errors;
- missing numeric values remaining unavailable rather than fabricated.

`tests/test_storage.py` covers R2 pointer namespace/traversal validation.

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
