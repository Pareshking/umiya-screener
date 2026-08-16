# Phase 7 — Production Operational Hardening Plan

**Started:** 2026-08-16

Phase 5 and Phase 6 are complete. Phase 7 is now the active workstream.

## Objective

Improve operational reliability of the deployed Screener without changing the quantitative methodology, canonical Adj Close + Volume contract, or Screener-only product scope.

## 7A — Observability and readiness

1. Separate liveness from readiness.
2. Expose safe dataset freshness/build information.
3. Add request correlation IDs where practical.
4. Make degraded/stale states explicit and machine-readable.

## 7B — Recovery and failure containment

1. Verify last-known-good metrics remain active after failed publication.
2. Verify R2 outage behavior and local-cache fallback.
3. Verify malformed pointer/dataset recovery.
4. Verify temporary downloads cannot replace a valid active dataset.

## 7C — Stale-data policy

1. Define the maximum acceptable metrics age.
2. Verify stale data produces a safe API state rather than being presented as current.
3. Verify the frontend has an understandable degraded/retry path.

## 7D — Scheduled operations

1. Verify weekday refresh schedule.
2. Verify failed refresh visibility/notification.
3. Verify production smoke coverage after refresh.
4. Verify R2 lifecycle retention cannot remove active pointers/current datasets.

## 7E — Security and abuse resistance

1. Review CORS and request handling.
2. Review expensive export behavior.
3. Confirm secrets never enter frontend bundles or normal logs.
4. Review dependency/security automation.

## 7F — Disaster/recovery acceptance

Simulate:

- failed data refresh
- unavailable R2
- stale metrics
- malformed active pointer

Then confirm the service fails safely and recovers after the next valid publication.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains canonical.
- Do not change quantitative methodology without explicit requirement and regression coverage.
- Prefer small, reversible operational changes.

## Phase 7 closure

Do not close Phase 7 until failure simulations, recovery checks, security review and documentation pass against the deployed production configuration.
