# Phase 7 — Production Operational Hardening

**Started:** 2026-08-16  
**Status:** ACTIVE

## Objective

Harden the already-production Screener for operational reliability without changing the quantitative/data contract or adding product scope.

## Scope

### 7A — Observability and readiness

- [ ] Separate liveness from readiness.
- [ ] Expose safe dataset/build freshness information.
- [ ] Add stable request correlation IDs to API responses/logs where practical.
- [ ] Ensure degraded/stale states are explicit and machine-readable.

### 7B — Recovery and failure containment

- [ ] Verify last-known-good dataset remains active when refresh/publication fails.
- [ ] Test R2 outage behavior and local-cache fallback.
- [ ] Test malformed pointer/dataset recovery.
- [ ] Ensure temporary downloads never replace a good active dataset.

### 7C — Stale-data policy

- [ ] Define explicit maximum acceptable metrics age.
- [ ] Verify frontend behavior for 503/degraded API state.
- [ ] Ensure stale data is never presented as current data.

### 7D — Scheduled operations

- [ ] Verify refresh schedule, failure notification and artifact retention.
- [ ] Verify production smoke coverage after refresh.
- [ ] Verify lifecycle retention does not delete active pointers/current datasets.

### 7E — Security and abuse resistance

- [ ] Review CORS, request limits and expensive export behavior.
- [ ] Confirm no secrets reach frontend bundles/logs.
- [ ] Review dependency/security automation.

### 7F — Disaster/recovery acceptance

- [ ] Simulate failed refresh.
- [ ] Simulate unavailable R2.
- [ ] Simulate stale metrics.
- [ ] Confirm service fails safely and recovers after the next good publication.
- [ ] Document recovery procedure.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains the canonical data contract.
- Do not change quantitative methodology without an explicit requirement and regression tests.
- Prefer small, reversible operational changes over architectural rewrites.

## Phase 7 closure rule

Close Phase 7 only after the operational failure simulations, recovery checks, security review and documentation all pass on the deployed production configuration.
