# Phase 8 — Next Audit / Work Plan

**Status:** ACTIVE — 2026-08-16

Phase 0–7 are complete. Phase 8 improves the existing production Screener without redesigning the architecture or changing quantitative methodology.

## 8A — Production UX audit

- Verify current desktop/mobile Screener behavior.
- Check loading, empty, error, READY and degraded/retry states.
- Identify concrete usability issues only.

## 8B — Correctness and edge cases

- Dynamic constituent-count changes and legitimate index membership changes.
- Empty-result filters and combined filters.
- Search + sort + pagination combinations.
- Extreme numeric values and null/missing metrics.
- Missing/insufficient history.
- Stock detail/chart valid, missing and newly appearing symbols.

## 8C — Data pipeline resilience

- Constituent ingestion and corporate-action handling.
- Refresh idempotency.
- Last-known-good behavior.
- R2 pointer safety and lifecycle interaction.

## 8D — API quality

- Schema/error semantics.
- Request IDs and cache policy.
- Request/response bounds and payload efficiency.
- Regression tests for every discovered contract issue.

## 8E — Performance/frontend polish

- Measure before optimizing.
- Re-check production latency only for evidence-backed targets.
- Mobile table usability.
- Chart interaction and loading behavior.

## 8F — Documentation/release discipline

- Keep README and status documents synchronized.
- Keep handover prompt current.
- Record production-facing contract changes with tests.
- Maintain a clean release/checkpoint procedure.

## Important constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains canonical.
- Do not silently change quantitative methodology.
- Do not hard-code the live universe to exactly 750.
- Do not make APCOTEXIND.NS part of production merely to satisfy a test.
- Do not optimize without measurement.

## First action for Phase 8

Start with **8A + 8B together**: inspect the current deployed frontend and API behavior, then run a systematic edge-case audit before adding features. Fix concrete defects found during that audit, test them, and update documentation in the same change.
