# Phase Status

**Updated:** 2026-08-16

## Completed

### Phase 0 — Architecture guardrails
Complete.

### Phase 1 — Data foundation
Complete: NSE constituent acquisition, 10-year Yahoo Adjusted Close + Volume contract, common `as_of`, history/freshness rules, coverage validation and provenance.

### Phase 2 — Quant engine
Complete: momentum/risk-adjusted metrics, ranking, technical snapshot and validation layer.

### Phase 3 — Query API + Screener UX
Complete: server-side filtering/search/sorting/pagination, metadata, export and responsive UI.

### Phase 4 — Stock detail
Complete: API-driven stock detail and adjusted-close charts.

### Phase 5 — Production deployment / hardening
**Implementation and automated validation complete. Formal closure still requires one external infrastructure check.**

Production integration is in place: GitHub Actions refresh, Cloudflare R2 immutable publication, Render FastAPI, Vercel Next.js, runtime R2 hydration, production CORS and production smoke validation.

Latest validation run on commit `05cea11ccf2e975e96aea3ff5293384e2d584f27` passed:

- Python test suite: **50 passed**
- Frontend build: **passed**
- 10-year Yahoo Adj Close + Volume validation: **passed**
- Real current-universe Phase 2 metric validation: **passed**
- Production smoke: **passed**

## Only remaining Phase 5 item

- [ ] **Verify/configure Cloudflare R2 object lifecycle/retention policy in the actual bucket.**

Requirements:

- historical immutable `datasets/` versions may expire after an agreed rollback window;
- historical immutable `metrics/` versions may expire after the same/agreed window;
- `pointers/` must not be accidentally expired;
- the active/latest dataset must remain available;
- incomplete multipart uploads should have a cleanup rule where appropriate;
- verify the actual bucket configuration, not only repository documentation.

Suggested initial retention: **30 days**, unless the required rollback window dictates otherwise.

## APCOTEXIND test clarification

`APCOTEXIND.NS` is **not a frontend-display test**. It is a data-pipeline/newly-injected-stock fixture only. Never alter the canonical production NSE universe solely to make this symbol appear in the UI.

## Phase 6 — Not started

After the R2 lifecycle gate is closed, formally start Phase 6 with deployed performance and UX measurement. Do not redesign the architecture before measurement.

Initial Phase 6 measurement sequence:

1. initial frontend load
2. unfiltered screener query
3. numeric filter
4. multi-filter
5. sort/search
6. stock detail/chart
7. p50/p95 latency
8. mobile UX
9. Render cold start and R2 bootstrap
10. data freshness/as-of verification

Only optimise measured bottlenecks.
