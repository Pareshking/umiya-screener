# Phase 6 — Production Measurement and Acceptance Plan

**Started:** 2026-08-16

Phase 5 is closed. The production R2 lifecycle policy has been configured and verified:

- `datasets/` → 30-day expiration
- `metrics/` → 30-day expiration
- `pointers/` → no expiration rule
- incomplete multipart uploads → 7-day abort

## Phase 6 objective

Measure and harden the deployed Vercel → Render → R2/API path without changing the quant/data contract unnecessarily.

## Automated benchmark

Use:

- `scripts/phase6_benchmark.py`
- `.github/workflows/phase6-benchmark.yml`

The benchmark measures repeated production HTTP timings for screener query, filters, search, sort, export, stock detail, 3M/6M/1Y charts and frontend response. It reports p50, p95 and max latency and uploads raw measurements as a GitHub Actions artifact.

The benchmark now preferentially selects `APCOTEXIND` when that symbol is present in the live universe, providing a controlled production-path check for the previously discussed injected-stock flow.

## 6A–6F status

- [x] Baseline benchmark recorded.
- [x] Chart cold-start bottleneck identified.
- [x] Startup price-dataset warming implemented.
- [x] Per-symbol chart caching implemented.
- [x] Chart endpoint aligned with current eligible stock universe.
- [x] Corporate-action/index-count resilience verified and covered by tests.
- [x] APCOTEXIND injected-stock pipeline test exists through Phase 1 → metrics → screener query.
- [x] Production CORS and secret-handling configuration audited at source level.
- [ ] Final production deployment of the latest commits.
- [ ] Final production smoke + Phase 6 benchmark on that same deployed commit.
- [ ] Final browser/mobile walkthrough, including APCOTEXIND when present.

## Initial production baseline

Seven runs per operation, all HTTP 200:

| Operation | p50 | p95 | Max |
|---|---:|---:|---:|
| Screener query | 73 ms | 96 ms | 96 ms |
| Numeric filter | 71 ms | 89 ms | 89 ms |
| Multi-filter | 72 ms | 94 ms | 94 ms |
| Search | 70 ms | 76 ms | 76 ms |
| Sort | 76 ms | 241 ms | 241 ms |
| Export | 343 ms | 596 ms | 596 ms |
| Stock detail | 64 ms | 66 ms | 66 ms |
| Chart 3M | 66 ms | 286 ms | 286 ms |
| Chart 6M | 67 ms | 83 ms | 83 ms |
| Chart 1Y | 68 ms | 88 ms | 88 ms |
| Frontend | 63 ms | 206 ms | 206 ms |

The earlier ~2.8 s 3M cold-start outlier was addressed by startup warming and chart caching.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Do not force the live universe to exactly 750 rows.
- Adj Close + Volume remains the canonical data contract.
- Do not turn unavailable long-history returns into artificial 0% values.
- Do not optimise without measurements.
