# Phase 9 — Production Release & Acceptance

**Status:** IN PROGRESS — 2026-08-16

Phase 9 is the final production acceptance checkpoint after the Phase 8 audit. It does not introduce architecture or quantitative-methodology changes.

## Scope

- Verify production GitHub Actions gates remain green.
- Validate the public Vercel frontend and Render API contract.
- Validate liveness, readiness and health behavior including Render cold starts.
- Record representative production query latency and payload sizes.
- Confirm invalid-request contracts, CORS, stock detail, charts and CSV export.
- Synchronize release documentation before moving to new product work.

## Current evidence

The latest pre-fix production run passed frontend build, Python tests, 10-year Yahoo history validation, Phase 2 real-universe validation, CodeQL, API queries, search/sort, stock detail, charts, export, HTTP 400/404 contracts, CORS and frontend reachability.

The only failing smoke assertion was readiness during a Render cold start. The service subsequently became healthy and all functional API checks passed, with query p50 43 ms / p95 44 ms in that run.

The smoke test has therefore been hardened to treat the first readiness request as a cold-start wake-up probe and require a readiness retry after liveness confirms the service is alive.

## Exit criteria

Phase 9 closes only when:

1. the updated production smoke workflow passes;
2. frontend, Python and security gates are green;
3. production API contracts remain green;
4. documentation is synchronized with the final evidence;
5. no known functional blocker remains.

An independent human visual walkthrough on a real desktop/mobile browser/device remains an external observation and is not represented as automated evidence.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains canonical.
- No silent quantitative-methodology changes.
- No optimization without measurement.
