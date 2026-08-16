# Umiya Screener V2

A clean, performance-first rebuild of the Umiya NSE quantitative screener.

> **Current status: Phase 5 production hardening complete; Phase 6 is next.**

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

The frontend never performs market-wide calculations. Filter, search, sort and pagination operate on prepared analytical data through the API. The API can hydrate the latest published dataset from R2 without rebuilding the market.

## Canonical universe

NSE 750 is the combination of:

- Nifty 50 — 50
- Nifty Next 50 — 50
- Nifty Midcap 150 — 150
- Nifty Smallcap 250 — 250
- Nifty Microcap 250 — 250

Total: **750 unique stocks**, with index membership retained.

## Canonical market-data contract

The production Phase 1 contract is intentionally limited to:

- Yahoo Finance **Adjusted Close**
- Yahoo Finance **Volume**
- exact 10-year historical window from build date
- common market `as_of` date
- minimum 126 valid observations
- maximum 3-calendar-day freshness
- explicit missing/invalid-data handling

Do not silently add OHLC fields. Metrics requiring High/Low must be explicitly redesigned and documented before implementation.

## Current API

```text
GET  /api/v1/health
GET  /api/v1/screener/metadata
POST /api/v1/screener/query
POST /api/v1/screener/export
GET  /api/v1/stocks/{symbol}
GET  /api/v1/stocks/{symbol}/chart
```

The API is a service/query layer, not a calculation notebook.

## Current frontend

The deployed frontend is API-driven and includes:

- screener table
- server-side search
- deterministic filtering
- sorting and pagination
- CSV export
- stock-detail route
- adjusted-close chart with 3M / 6M / 1Y ranges
- loading, empty and error states
- mobile-first responsive behaviour

No production fallback uses fake or hard-coded financial data.

## Data refresh / R2

GitHub Actions builds and validates new datasets before publication. Published datasets are immutable. `LATEST.json`-style pointers select the currently valid dataset. A failed build must never replace the previous good pointer.

Production GitHub Actions R2 secrets are:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Never commit these values.

## Validation

The repository has automated validation for:

- quantitative/data-policy unit tests
- real NSE 750 + Yahoo historical validation
- metrics validation
- frontend production build
- production API smoke testing
- API error handling
- production CORS
- stock detail and chart endpoints

The production smoke workflow also exercises the deployed Vercel frontend and records query latency.

### APCOTEXIND end-to-end test

`APCOTEXIND.NS` is used as an opt-in newly-injected-stock test case. It verifies that a stock entering the universe can travel through Yahoo ingestion → validation → metrics → publication → API → frontend without special-case code.

The test fixture must **not** permanently alter the canonical production NSE 750 universe merely to make the stock appear in the UI.

## Phase history

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture / guardrails | ✅ Complete |
| 1 | NSE 750 + 10Y Adj Close/Volume foundation | ✅ Complete |
| 2 | Quantitative engine / metrics | ✅ Complete |
| 3 | Query API + screener UX | ✅ Complete |
| 4 | Stock detail + charts | ✅ Complete |
| 5 | Production deployment / R2 / CI / hardening | ✅ Complete |
| 6 | Real-world validation, performance and bottleneck work | **Next** |
| 7 | Production hardening / observability / recovery | Planned |
| 8 | Future Umiya modules | Later |

## Phase 6 starting point

Do not redesign the architecture at the start of Phase 6. First measure the deployed system.

1. Run production performance measurements for initial load, unfiltered query, filter, multi-filter, sort, search and stock detail.
2. Capture p50/p95 and identify the actual bottleneck.
3. Test mobile UX on a real device.
4. Validate live data freshness and displayed `as_of` values.
5. Run the APCOTEXIND injected-stock path end-to-end.
6. Test Render restart/cold-start and R2 bootstrap.
7. Only then make targeted optimisations.

## Working rules for future changes

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

Start here when returning to the project:

- `docs/PROJECT_CONTEXT.md` — current project state and decisions
- `docs/ARCHITECTURE.md` — system boundaries and data flow
- `docs/PHASE_STATUS.md` — phase history and exact next gates
- `docs/DATA_CONTRACT.md` — canonical data and freshness rules
- `docs/OPERATIONS_RUNBOOK.md` — deployment, refresh, recovery and secrets
- `docs/VALIDATION.md` — test strategy and production audit
- `docs/PHASE5_CHECKLIST.md` — Phase 5 historical checklist
- `docs/PHASE5_SECRETS.md` — production R2 secret names
- `docs/NEXT_AUDIT.md` — remaining audit/maintenance guidance

## Local development

Backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Run API locally:

```bash
uvicorn backend.app.main:app --reload
```

Run frontend:

```bash
cd frontend
npm ci
npm run dev
```

Run tests:

```bash
pytest -q
```

## Important repository boundary

`Pareshking/Umiya` is not part of this codebase's implementation path. It is a reference source only. The V2 repository must remain independently understandable and deployable.
