# Phase 7 — Production Operational Hardening

**Status: COMPLETE — 2026-08-16**

## Objective

Harden the production Screener for operational reliability without changing the quantitative methodology, canonical Adj Close + Volume contract, or Screener-only product scope.

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
- [x] Last-known-good local metrics cache remains available when R2 synchronization fails.
- [x] Empty remote prefixes are rejected.
- [x] Malformed pointers are rejected.
- [x] Temporary downloads are validated before replacing the active dataset.
- [x] Object-store download path traversal is rejected.

## 7C — Stale-data policy

- [x] Maximum metrics age is explicitly 24 hours.
- [x] Stale metrics return a safe degraded API state.
- [x] Frontend has an explicit degraded/retry path.
- [x] Dataset `built_at` and `market_as_of` remain visible when healthy.

## 7D — Scheduled operations

- [x] Weekday refresh remains scheduled at 13:30 UTC / 19:00 IST.
- [x] Refresh uses immutable R2 publication followed by pointer advancement.
- [x] Post-publication production readiness smoke is part of the refresh workflow.
- [x] Refresh failure is visible through GitHub Actions.
- [x] R2 lifecycle policy is configured and verified: datasets/metrics 30 days, pointers protected, incomplete multipart uploads 7 days.
- [x] Controlled real refresh completed successfully on 2026-08-16.

## 7E — Security and abuse resistance

- [x] Production CORS remains allow-list based.
- [x] API request bodies are capped at 256 KiB.
- [x] Screener page size is capped at 200 rows and export is bounded.
- [x] API responses are not browser-cacheable.
- [x] No production secret is read by the frontend bundle.
- [x] Dependabot remains enabled and CodeQL covers Python and TypeScript/JavaScript.

## 7F — Disaster/recovery acceptance

Automated coverage passed for failed/unavailable metrics readiness, empty object-store prefixes, unsafe paths, safe temporary dataset download, request-size rejection and explicit degraded frontend state.

## Production acceptance record

- [x] Phase 7 implementation merged to `main`.
- [x] Final validation passed.
- [x] CodeQL security workflows passed.
- [x] Production smoke passed, including liveness/readiness, metadata, query/search/sort, stock detail, charts, export, CORS and frontend availability.
- [x] Vercel deployment reported successful.
- [x] Controlled real data refresh completed successfully.
- [x] Post-publication production readiness smoke passed.

### Manual visual observation

A manual browser/mobile walkthrough of the READY/DEGRADED UI was not independently performed by the repository tooling. This is an observation limitation, not a known production defect; automated API and production gates are green.

## Phase 7 closure

**Phase 7 is formally closed.** Future work begins in Phase 8 as documented by `docs/NEXT_AUDIT.md` and `docs/PHASE_STATUS.md`.
