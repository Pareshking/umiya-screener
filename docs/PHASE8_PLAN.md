# Phase 8 — Production Screener Evolution Plan

**Started:** 2026-08-16  
**Status:** ACTIVE

## Objective

Improve the existing production Screener based on evidence from real usage and systematic testing. This phase is **not** an architecture redesign and does not change the quantitative methodology without an explicit requirement.

## 8A — Production UX audit

- Audit desktop and mobile Screener layout.
- Verify loading, empty, error, READY and degraded/retry states.
- Check table usability, search/filter controls, pagination, export and stock-detail navigation.
- Identify concrete UX defects before changing UI behavior.

## 8B — Correctness and edge-case audit

Test:

- dynamic constituent counts;
- legitimate index membership/corporate-action changes;
- empty-result filters;
- combined filters;
- search + sort + pagination;
- null/missing metric values;
- extreme numeric values;
- insufficient historical observations;
- valid, missing and newly appearing stock symbols;
- chart ranges and insufficient chart history.

Expected behavior must follow the canonical data contract. Missing data remains missing; no fabricated returns.

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

Every contract change gets regression coverage and documentation.

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
