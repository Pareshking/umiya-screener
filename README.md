# Umiya Screener V2

A clean, performance-first rebuild of the Umiya NSE quantitative screener.

> **Current status: Phase 0–9 complete.**

The old `Pareshking/Umiya` repository is **reference-only and must never be modified**. It is used for quantitative methodology, validated formulas, research requirements and product behaviour—not as an architectural template.

## Production

- Frontend: https://pareshpatel.vercel.app/
- API: https://umiya-screener-api.onrender.com/
- API docs: `https://umiya-screener-api.onrender.com/docs`
- Health: `/api/v1/health`
- Liveness: `/api/v1/live`
- Readiness: `/api/v1/ready`
- Production smoke workflow: `.github/workflows/production-smoke.yml`
- Scheduled data refresh: `.github/workflows/data-refresh.yml`

## Architecture

```text
Official NSE constituents
        ↓
Yahoo Finance Adj Close + Volume
        ↓
Validated 10-year dataset
        ↓
Quantitative metrics
        ↓
Validation / provenance / versioning
        ↓
Cloudflare R2 immutable datasets + latest pointers
        ↓
FastAPI on Render (read-only query service)
        ↓ JSON/HTTP
Next.js on Vercel
```

The frontend never performs market-wide calculations. Filter, search, sort and pagination operate on prepared analytical data through the API.

## Canonical universe

The project targets the NSE 750 universe, formed from Nifty 50, Nifty Next 50, Nifty Midcap 150, Nifty Smallcap 250 and Nifty Microcap 250. The live constituent count **must not be hard-coded to exactly 750**; legitimate index membership and corporate-action changes are tolerated while catastrophic incompleteness is rejected.

## Canonical market-data contract

Production market data is limited to:

- Yahoo Finance Adjusted Close
- Yahoo Finance Volume
- last 10 years from build date
- common market `as_of` date
- minimum 126 valid observations
- maximum 3-calendar-day freshness
- price and volume freshness validated independently

Do not silently add OHLC fields. Metrics requiring High/Low must be explicitly redesigned and documented.

Missing long-history data remains unavailable; the system must never manufacture missing returns as 0%.

## Current API

```text
GET  /api/v1/live
GET  /api/v1/ready
GET  /api/v1/health
GET  /api/v1/screener/metadata
POST /api/v1/screener/query
POST /api/v1/screener/export
GET  /api/v1/stocks/{symbol}
GET  /api/v1/stocks/{symbol}/chart
```

## Current frontend

The production frontend is API-driven and includes the Screener table, search, filtering, sorting, pagination, CSV export, stock detail and adjusted-close charts.

## Data refresh / R2

GitHub Actions builds and validates new datasets before publication. Published datasets are immutable. Latest-pointer objects select the active dataset. A failed build must never replace the previous good pointer.

The production R2 lifecycle policy is verified as:

- `datasets/` → 30-day historical retention
- `metrics/` → 30-day historical retention
- `pointers/` → protected from the historical expiration rule
- incomplete multipart uploads → 7-day cleanup

Production GitHub Actions R2 secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Never commit these values.

## APCOTEXIND test clarification

`APCOTEXIND.NS` is a newly-injected-stock/data-pipeline test fixture. It is **not intended to be shown in the production frontend** and must not be permanently added to the canonical universe merely to make a UI test pass.

## Phase history

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture / guardrails | ✅ Complete |
| 1 | NSE 750 + 10Y Adj Close/Volume foundation | ✅ Complete |
| 2 | Quantitative engine / metrics | ✅ Complete |
| 3 | Query API + screener UX | ✅ Complete |
| 4 | Stock detail + charts | ✅ Complete |
| 5 | Production deployment / R2 / CI / hardening | ✅ Complete |
| 6 | Production measurement, correctness and performance | ✅ Complete |
| 7 | Production operational hardening | ✅ Complete |
| 8 | Production Screener evolution / edge-case audit | ✅ Complete |
| 9 | Production release & acceptance | ✅ Complete |

## Phase 9 closure

Phase 9 completed the final production acceptance checkpoint without changing architecture or quantitative methodology. The production smoke suite passed readiness, liveness, health, metadata, five screener queries, search/sort, stock detail, all three chart horizons, CSV export, 400/404 contracts, CORS and frontend reachability. The passing run recorded query latency of p50 103 ms / p95 106 ms.

The smoke test was hardened to handle Render cold starts correctly: the initial readiness request acts as a wake-up probe, liveness confirms availability, and readiness is retried and required to establish dataset readiness.

Frontend build, Python/data-validation gates and CodeQL were green on the release checkpoint. Phase 9 is now closed.

## Working rules

- Do not reintroduce Streamlit architecture or rerun-style behaviour.
- Do not move financial calculations into React/TypeScript.
- Do not download market data in response to a UI filter/search.
- Do not use ephemeral API-local storage as the production source of truth.
- Do not display invented/demo market data in production.
- Do not optimise without a measurement.
- Do not add other Umiya tabs until the Screener is production-quality.
- Preserve methodology only after verifying the original Umiya implementation.
- Keep data pipeline, quantitative engine, API and frontend independently testable.
- Update implementation, tests and documentation together for contract changes.

## Documentation map

- `docs/PROJECT_CONTEXT.md` — current project context and guardrails
- `docs/ARCHITECTURE.md` — system boundaries and data flow
- `docs/PHASE_STATUS.md` — current phase state
- `docs/NEXT_AUDIT.md` — Phase 8 closure record
- `docs/DATA_CONTRACT.md` — canonical data and freshness rules
- `docs/OPERATIONS_RUNBOOK.md` — deployment, refresh, recovery and secrets
- `docs/VALIDATION.md` — test strategy and production audit
- `docs/PRODUCTION_STORAGE.md` — R2 publication/storage design
- `docs/PHASE5_STATUS.md` — Phase 5 closure record
- `docs/PHASE6_STATUS.md` — Phase 6 benchmark/acceptance record
- `docs/PHASE7_STATUS.md` — Phase 7 acceptance record
- `docs/PHASE8_AUDIT.md` — Phase 8 findings and fixes
- `docs/PHASE8_PLAN.md` — Phase 8 closure plan
- `docs/PHASE9_RELEASE.md` — Phase 9 production release checkpoint
- `docs/HANDOVER_PROMPT.md` — continuation prompt for future AI sessions
