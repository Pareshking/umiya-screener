# Umiya Screener V2

A clean, performance-first rebuild of the Umiya NSE quantitative screener.

> **Current status: Phase 5 is in final housekeeping. Phase 6 has not formally started.**

The old `Pareshking/Umiya` repository is **reference-only and must never be modified**. It is used for quantitative methodology, validated formulas, research requirements and product behaviour—not as an architectural template.

## Production

- Frontend: https://pareshpatel.vercel.app/
- API: https://umiya-screener-api.onrender.com/
- API docs: `https://umiya-screener-api.onrender.com/docs`
- Production health: `/api/v1/health`
- Production smoke workflow: `.github/workflows/production-smoke.yml`
- Scheduled data refresh: `.github/workflows/data-refresh.yml`

## Architecture

```text
Official NSE constituents
        ↓
Yahoo Finance Adj Close + Volume
        ↓
Phase 1 validated 10-year dataset
        ↓
Phase 2 quantitative metrics
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

NSE 750 is the combination of Nifty 50, Nifty Next 50, Nifty Midcap 150, Nifty Smallcap 250 and Nifty Microcap 250: **750 unique stocks**.

## Canonical market-data contract

Production Phase 1 data is limited to:

- Yahoo Finance Adjusted Close
- Yahoo Finance Volume
- last 10 years from build date
- common market `as_of` date
- minimum 126 valid observations
- maximum 3-calendar-day freshness

Do not silently add OHLC fields. Metrics requiring High/Low must be explicitly redesigned and documented.

## Current API

```text
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

Production GitHub Actions R2 secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Never commit these values.

## Phase 5 final housekeeping

Everything required for production deployment and runtime integration has been completed. **Exactly one Phase 5 item remains:**

> **Verify/configure the Cloudflare R2 object lifecycle/retention policy so old immutable dataset versions do not accumulate indefinitely.**

The lifecycle policy must protect the active/latest pointers. It should apply to immutable historical dataset prefixes such as `datasets/` and `metrics/`, not to `pointers/`.

The current repository does not itself prove that the Cloudflare bucket lifecycle rule is configured; this is an external bucket-level configuration and must be verified in the R2 account.

## APCOTEXIND test clarification

`APCOTEXIND.NS` was **not intended to be shown in the production frontend**. It is only a newly-injected-stock/data-pipeline test fixture. The test must not be described as an end-to-end frontend-stock test, and the canonical production NSE 750 universe must not be altered merely to display this symbol.

## Phase history

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture / guardrails | ✅ Complete |
| 1 | NSE 750 + 10Y Adj Close/Volume foundation | ✅ Complete |
| 2 | Quantitative engine / metrics | ✅ Complete |
| 3 | Query API + screener UX | ✅ Complete |
| 4 | Stock detail + charts | ✅ Complete |
| 5 | Production deployment / R2 / CI / hardening | **Final housekeeping only** |
| 6 | Real-world validation, performance and bottleneck work | **Next — not started** |
| 7 | Production hardening / observability / recovery | Planned |

## Phase 6 starting point

Only after the R2 lifecycle/retention item is verified/configured should Phase 5 be formally closed and Phase 6 begin.

Phase 6 then starts with measurement: initial load, API query/filter/search/sort latency, stock detail/chart latency, mobile UX, cold-start/R2 bootstrap and real-world data freshness.

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

## Documentation map

- `docs/PROJECT_CONTEXT.md` — current project state and decisions
- `docs/ARCHITECTURE.md` — system boundaries and data flow
- `docs/PHASE_STATUS.md` — phase history and exact next gates
- `docs/DATA_CONTRACT.md` — canonical data and freshness rules
- `docs/OPERATIONS_RUNBOOK.md` — deployment, refresh, recovery and secrets
- `docs/VALIDATION.md` — test strategy and production audit
- `docs/PHASE5_CHECKLIST.md` — Phase 5 final checklist
- `docs/NEXT_AUDIT.md` — next required action
