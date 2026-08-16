# Phase 8 — Production Screener Evolution Plan

**Started:** 2026-08-16  
**Status:** ACTIVE — 8C–8F in progress

## Objective

Improve the existing production Screener based on evidence from real usage and systematic testing. This phase is **not** an architecture redesign and does not change the quantitative methodology without an explicit requirement.

## 8A — Production UX audit

- [x] Inspect current production Screener frontend structure and error/loading/degraded paths.
- [x] Inspect stock-detail loading/error/chart cancellation behavior.
- [x] Identify stale-response race in the main Screener query path.
- [x] Fix stale-response race using per-query `AbortController` cancellation.
- [x] Separate data degradation from ordinary request/contract errors.
- [x] Make the mobile filter search control functional.
- [x] Restore saved-screen state safely on subsequent visits.
- [ ] Complete independent manual browser/mobile walkthrough; repository automation cannot perform a human visual observation.

## 8B — Correctness and edge cases

- [x] dynamic constituent counts are data-driven;
- [x] legitimate index membership/corporate-action changes are not forced to exactly 750 rows;
- [x] empty-result filters have an explicit UI state;
- [x] combined filters are applied server-side in sequence;
- [x] search + sort + pagination are server-side;
- [x] null/missing metric values remain null/blank;
- [x] extreme numeric filter values are handled through numeric coercion and empty results where appropriate;
- [x] numeric equality filters coerce numeric string values consistently;
- [x] insufficient historical observations remain unavailable rather than fabricated;
- [x] missing/new symbols are rejected unless present in the current eligible universe;
- [x] chart ranges are bounded by the API;
- [x] unsupported sort fields now return an explicit API contract error instead of silently falling back to Rank;
- [x] out-of-range pages are clamped to the last available page when matches exist;
- [x] dedicated regression coverage added for pagination boundaries and edge-case query combinations;
- [x] CI validation passed for the preceding Phase 8 regression-test checkpoint.

## 8C — Data pipeline resilience

- [x] Review current constituent acquisition and dynamic-count safeguards.
- [x] Review duplicate constituent handling and current-universe construction.
- [x] Review immutable local dataset publication and latest-pointer update ordering.
- [x] Review last-known-good metrics fallback and temporary-download validation.
- [x] Add R2 pointer target validation helper and regression coverage for traversal/namespace violations.
- [ ] Complete production R2 pointer/lifecycle verification against the active bucket after the latest code changes.
- [ ] Add/execute explicit refresh-idempotency regression coverage.
- [ ] Complete corporate-action/index-membership change scenario coverage.

## 8D — API quality

- [x] Review request IDs and no-store response behavior.
- [x] Review schema bounds and request-size protection.
- [x] Review sort/filter error semantics.
- [x] Review response payload fields; current query response retains compatibility fields used by the API contract.
- [ ] Add focused API response-size measurements for representative query/search/export requests.
- [ ] Complete deployed API contract smoke after the latest commits.

## 8E — Performance and frontend polish

- [x] Existing production smoke records repeated query latency and p50/p95.
- [x] Avoided optimization without measured evidence.
- [ ] Re-run production latency measurements after 8C/8D changes.
- [ ] Complete manual/mobile rendering observation where a human browser is available.
- [ ] Review chart interaction and loading behavior on a real device.

## 8F — Documentation/release discipline

- [x] Synchronize Phase 5/R2 production-storage documentation with the actual closed state.
- [x] Record Phase 8 audit findings and regression coverage.
- [ ] Synchronize README, `PHASE_STATUS.md`, `NEXT_AUDIT.md` and `HANDOVER_PROMPT.md` after 8C–8E closure.
- [ ] Record a clean Phase 8 release/checkpoint once all gates pass.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains canonical.
- Do not hard-code the live universe to exactly 750.
- Do not permanently add `APCOTEXIND.NS` merely to make a frontend test pass.
- Do not silently change quantitative methodology.
- Do not optimize without measurement.
