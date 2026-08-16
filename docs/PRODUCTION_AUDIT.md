# Production Audit — 2026-08-16

## Gate 1 — Data publication

- [x] GitHub Actions builds canonical 10-year dataset
- [x] Metrics build completes
- [x] Dataset validation completes
- [x] Immutable R2 versions are uploaded
- [x] Latest pointer is advanced only after successful upload
- [x] Manual refresh works

## Gate 2 — Application delivery

- [x] Vercel production deployment succeeds
- [x] Live frontend loads
- [x] Live screener query returns ranked results
- [x] API-driven architecture confirmed

## Gate 3 — Fresh-instance recovery

- [x] R2 pointer contract is explicitly tested
- [x] Fresh API bootstrap path is covered by automated test
- [ ] Perform a real cold-start test against the deployed API
- [ ] Confirm production API has no dependency on a bundled local price dataset

## Gate 4 — Production API

- [ ] Verify `/api/v1/health` externally
- [ ] Verify `/api/v1/screener/metadata`
- [ ] Verify filtered query
- [ ] Verify search and sorting
- [ ] Verify CSV export
- [ ] Verify stock detail
- [ ] Verify chart endpoint
- [ ] Restrict CORS to production frontend origin

## Gate 5 — UX and performance

- [ ] Mobile smoke test
- [ ] Desktop smoke test
- [ ] Stock-detail deep link
- [ ] Error/stale-data UI
- [ ] Record p50/p95 query latency
- [ ] Verify repeated-query behavior

## Gate 6 — Operational resilience

- [ ] Simulate failed refresh and verify previous pointer remains live
- [ ] Verify scheduled refresh after market close
- [ ] Verify R2 immutable-version retention/cleanup policy
- [ ] Add operational monitoring/alert path if required

**Rule:** no new product features until Gates 3–6 are complete.
