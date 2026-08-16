# Phase 7 — Production Operational Hardening

**Started:** 2026-08-16  
**Status:** ACCEPTANCE — implementation and automated production gates passed; manual browser walkthrough remains

## Objective

Harden the already-production Screener for operational reliability without changing the quantitative/data contract or adding product scope.

## 7A — Observability and readiness

- [x] Separate liveness from readiness: `/api/v1/live` and `/api/v1/ready`.
- [x] Readiness requires a usable, non-stale metrics dataset.
- [x] Safe `built_at`, `market_as_of`, row count and canonical data contract are exposed.
- [x] Stable `X-Request-ID` response header is generated or propagated.
- [x] API responses are explicitly `Cache-Control: no-store`.
- [x] Health reports the 24-hour metrics freshness policy.
- [x] Production smoke verifies liveness/readiness on the deployed API.

## 7B — Recovery and failure containment

- [x] Immutable dataset is uploaded before the R2 pointer advances.
- [x] Existing last-known-good local metrics cache remains available when R2 synchronization fails.
- [x] Empty remote prefixes are rejected.
- [x] Malformed pointers are rejected and do not become local active datasets.
- [x] Temporary downloads are validated before replacing the local active dataset.
- [x] Object-store download path traversal is rejected.

## 7C — Stale-data policy

- [x] Maximum metrics age is explicitly 24 hours.
- [x] Stale metrics return a safe 503/degraded state rather than being presented as current.
- [x] Frontend explicitly displays `DEGRADED` and provides retry behavior.
- [x] Dataset `built_at` and `market_as_of` remain visible when healthy.

## 7D — Scheduled operations

- [x] Weekday refresh remains scheduled at 13:30 UTC / 19:00 IST.
- [x] Refresh uses immutable R2 publication followed by pointer advancement.
- [x] Post-publication production smoke checks `/live`, `/ready` and screener metadata.
- [x] GitHub workflow failure remains visible through normal Actions failure notifications.
- [x] R2 lifecycle policy is configured: datasets/metrics 30 days, pointers protected, incomplete multipart uploads 7 days.

## 7E — Security and abuse resistance

- [x] Production CORS remains allow-list based.
- [x] API request bodies are capped at 256 KiB.
- [x] Existing screener page size is capped at 200 rows; export is bounded by the live screener universe.
- [x] API responses are not browser-cacheable.
- [x] No production secret is read by the frontend bundle.
- [x] Dependabot remains enabled and CodeQL analysis covers Python and TypeScript/JavaScript.

## 7F — Disaster/recovery acceptance

Automated coverage added for:

- [x] failed/unavailable metrics readiness
- [x] empty object-store prefix
- [x] unsafe object-store paths
- [x] safe temporary dataset download behavior
- [x] request-size rejection
- [x] explicit degraded frontend state

## Production acceptance record

- [x] Phase 7 PR merged to `main` as commit `667c4c1950a5af2c850a42d3a308a642fc58e190`.
- [x] Final validation workflow passed on the merged commit.
- [x] Final CodeQL security workflow passed on the merged commit.
- [x] Production smoke passed on the merged commit, including liveness, readiness, health, metadata, query/search/sort, stock detail, charts, export, CORS and frontend HTTP availability.
- [x] Vercel deployment status reported successful for the Phase 7 merged deployment.
- [ ] Manual browser/mobile walkthrough of READY/DEGRADED UI states.
- [ ] Observe one future scheduled refresh completing successfully without an invalid pointer advance.

The remaining two items are acceptance/operational observation gates rather than missing Phase 7 implementation.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Adj Close + Volume remains the canonical data contract.
- Do not change quantitative methodology without an explicit requirement and regression tests.
- Prefer small, reversible operational changes over architectural rewrites.

## Phase 7 closure rule

Close Phase 7 after the manual UI walkthrough and one normal scheduled refresh observation are completed. No further code changes are required for those gates unless an actual failure is discovered.
