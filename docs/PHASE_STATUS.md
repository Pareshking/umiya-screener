# Phase Status

**Updated:** 2026-08-16

## Completed

### Phase 0 — Architecture guardrails

Complete.

### Phase 1 — Data foundation

Complete: NSE 750 acquisition, 10-year Yahoo Adjusted Close + Volume contract, freshness/history rules, validation and provenance.

### Phase 2 — Quant engine

Complete: prepared screener metrics, ranking and validation layer.

### Phase 3 — Query API + Screener UX

Complete: server-side filtering/search/sorting/pagination, metadata, export and responsive UI.

### Phase 4 — Stock detail

Complete: API-driven stock detail and adjusted-close charts.

### Phase 5 — Production deployment / hardening

**Implementation complete. Final housekeeping only.**

Production integration is in place: GitHub Actions refresh, Cloudflare R2 immutable publication, Render FastAPI, Vercel Next.js, runtime R2 hydration, production CORS and production smoke validation.

## Only remaining Phase 5 item

- [ ] **Verify/configure Cloudflare R2 object lifecycle/retention policy.**

Purpose: prevent old immutable `datasets/` and `metrics/` versions from accumulating indefinitely.

Requirements:

- historical immutable versions may expire after an agreed retention period;
- `pointers/` must not be accidentally expired;
- the active/latest dataset must remain available;
- incomplete multipart uploads should have a cleanup rule where appropriate;
- verify the rule in the actual R2 bucket, not only in repository documentation.

Suggested initial retention: **30 days**, unless a different rollback requirement is chosen.

## APCOTEXIND test clarification

`APCOTEXIND.NS` is **not a frontend-display test**. It was never intended to appear in the production frontend. It is a data-pipeline/newly-injected-stock test fixture and must remain separate from the canonical production NSE 750 membership.

## Phase 6 — Not started

After the R2 lifecycle gate is closed, formally start Phase 6 with real-world performance and UX measurement. Do not redesign the architecture before measurement.

First Phase 6 gates:

1. initial frontend load
2. screener query/filter/search/sort latency
3. p50/p95 measurements
4. stock detail/chart latency
5. mobile UX
6. Render cold start/R2 bootstrap
7. data freshness/as-of verification
