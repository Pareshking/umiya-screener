# Phase 6 — Production Audit Status

**Started:** 2026-08-16  
**Status:** ACTIVE — final acceptance in progress

## Scope

Phase 6 is the production measurement, correctness and hardening pass after Phase 5 deployment.

### 6A — Chart consistency and caching

- Production chart latency measured before optimization.
- Startup warming and per-symbol in-process chart caching added.
- Chart access is now aligned with the current eligible screener universe; direct chart requests cannot bypass stock eligibility.
- Re-benchmark after the latest production deployment is required before closing 6A.

### 6B — Frontend/API failure-state audit

Verified in source:

- API failures surface as retryable screener errors.
- Stock detail uses abortable requests to avoid stale navigation results.
- CORS is restricted to configured origins; production defaults to the Vercel production URL.
- API returns 400 for invalid filters and 404 for unavailable stocks/charts.
- Health endpoint reports `ok` vs `degraded` based on metrics-cache readiness.

Remaining acceptance check: production browser/mobile walkthrough after latest deployment.

### 6C — Data freshness and scheduled refresh

- Weekday GitHub Actions refresh: 13:30 UTC (19:00 IST).
- Canonical 10-year dataset is rebuilt before metrics.
- Generated datasets are validated before R2 publication.
- Render metrics cache has a 24-hour TTL and reports degraded/stale state when exceeded.
- Dataset metadata exposes `market_as_of` and `built_at` to the frontend.

### 6D — Corporate actions / universe resilience

The universe loader intentionally treats configured index counts as reference counts, not fixed requirements.

- A legitimate change such as NIFTY 50 moving from 50 to 51 constituents is accepted and recorded as a warning.
- Catastrophic drops are rejected using per-index and total-universe minimum ratios.
- Symbols are normalized and de-duplicated.
- Existing tests explicitly cover the 50 -> 51 case and reject a 30-member NIFTY 50 source.
- APCOTEXIND has an end-to-end injected-stock test through Phase 1, metrics and screener query.

### 6E — Security/configuration audit

- Production CORS is allow-list based.
- R2 credentials are supplied through GitHub/Render secrets, not repository files.
- Immutable R2 datasets use lifecycle retention; pointers are protected.
- No production secret is required by the frontend bundle.
- Dependency review and Dependabot workflows are enabled.

### 6F — Final production acceptance

Required gates before Phase 6 closure:

1. Latest code validation green.
2. Production smoke green.
3. Phase 6 benchmark green after the final code deployment.
4. APCOTEXIND production search/detail/chart path verified when present in the current universe.
5. Frontend mobile/browser walkthrough completed.
6. Documentation updated with final benchmark and deployment commit.

## Production baseline

Initial Phase 6 benchmark, 7 requests per operation, all HTTP 200:

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

The earlier 3M cold-start outlier (~2.8 s) was addressed with dataset startup warming and chart caching.

## Closure rule

Do not declare Phase 6 complete merely because CI is green. Close it only after the final production smoke + benchmark + browser/mobile acceptance gates above pass on the same deployed commit.
