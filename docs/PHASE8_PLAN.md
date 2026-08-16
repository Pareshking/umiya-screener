# Phase 8 — Production Screener Evolution Plan

**Started:** 2026-08-16  
**Status:** ACTIVE — 8A/8B in progress

## Objective

Improve the existing production Screener based on evidence from real usage and systematic testing. This phase is **not** an architecture redesign and does not change the quantitative methodology without an explicit requirement.

## 8A — Production UX audit

- [x] Inspect current production Screener frontend structure and error/loading/degraded paths.
- [x] Inspect stock-detail loading/error/chart cancellation behavior.
- [x] Identify stale-response race in the main Screener query path.
- [x] Fix stale-response race using per-query `AbortController` cancellation.
- [ ] Complete production browser/mobile walkthrough.

## 8B — Correctness and edge-case audit

Reviewed and/or covered in the current implementation:

- [x] dynamic constituent counts are data-driven;
- [x] legitimate index membership/corporate-action changes are not forced to exactly 750 rows;
- [x] empty-result filters have an explicit UI state;
- [x] combined filters are applied server-side in sequence;
- [x] search + sort + pagination are server-side;
- [x] null/missing metric values remain null/blank;
- [x] extreme numeric filter values are handled through numeric coercion and empty results where appropriate;
- [x] insufficient historical observations remain unavailable rather than fabricated;
- [x] missing/new symbols are rejected unless present in the current eligible universe;
- [x] chart ranges are bounded by the API;
- [ ] add/execute dedicated regression coverage for pagination boundaries and edge-case query combinations;
- [ ] verify real production edge cases after the next validation run.

## 8C — Data pipeline resilience

Review:

- constituent acquisition;
- duplicate constituent handling;
- refresh idempotency;
- last-known-good behavior;
- R2 pointer safety;
- lifecycle interaction with active datasets;
- corporate-action/index membership changes.

## 8D — API quality

Review:

- schema consistency;
- validation/error semantics;
- request IDs;
- no-store behavior;
- request-size limits;
- response payload size;
- export bounds;
- unnecessary fields or duplicate work.

Known observation: unsupported sort fields currently fall back to `Rank`. Review whether this should become an explicit validation error as part of 8D; do not change it solely for cosmetic strictness without regression coverage.

## 8E — Performance and frontend polish

Measure before optimizing.

Targets include:

- initial load;
- screener query/filter/search/sort;
- stock detail;
- charts;
- export;
- mobile rendering;
- API payload size;
- Render cold start where relevant.

Only evidence-backed bottlenecks should be optimized.

## 8F — Documentation/release discipline

- Keep README synchronized with actual production state.
- Keep `PHASE_STATUS.md`, `NEXT_AUDIT.md` and phase documents current.
- Keep `HANDOVER_PROMPT.md` current.
- Record production-facing contract changes with tests.
- Maintain clean release/checkpoint notes.

## First execution order

**8A + 8B together.**

1. Inspect current deployed frontend/API.
2. Run a systematic edge-case audit.
3. Record findings.
4. Fix concrete defects.
5. Test and build.
6. Run production smoke for production-facing fixes.
7. Update documentation.

Do not add unrelated product modules during this audit.

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
