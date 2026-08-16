# Umiya Screener V2

A clean, performance-first rebuild of the Umiya NSE quantitative screener.

> **Current status: Phases 0–9 complete; Phase 10 UI/UX release candidate ready for final Vercel deployment and human review.**

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

## Phase 10 release candidate

The current `main` branch contains the Phase 10 product-facing UI/UX release candidate for both the Screener and individual stock research pages.

The source work is complete and production API validation remains green. Vercel deployment capacity has recovered: a recent Vercel deployment reached **Ready**, but that deployment corresponds to the older `431feb7` commit. The latest Phase 10 `main` source still needs one successful Vercel deployment before final human acceptance.

Do not treat the older Vercel deployment as the final Phase 10 UI review target.

## Phase 10 UI/UX goals

The original Streamlit application is the baseline to beat, not the design to copy. Phase 10 aims for a purpose-built quantitative research website: fast, clear, information-dense without clutter, polished on desktop/tablet/mobile, and substantially better to use than the original Streamlit interface.

### Screener

- stronger visual hierarchy and typography;
- balanced KPI cards;
- clearer filter cards and active-filter chips;
- improved search, sort, column and export controls;
- sticky table headers and better result scanning;
- purpose-built mobile result cards;
- mobile filter drawer and bottom navigation;
- responsive tablet layout;
- clearer loading, empty, error and degraded states;
- improved focus and interaction states.

### Individual stock research

- redesigned research hero and stock identity;
- prominent momentum rank/score, CMP and 12-month return;
- explicit 200 EMA trend status;
- larger adjusted-close price-structure chart with range selection;
- Momentum & Returns section;
- Technical Structure section;
- Research Context / dataset provenance;
- responsive mobile research layout;
- clearer navigation and research actions.

No quantitative methodology, API contract, server-side calculation or data architecture changes are part of Phase 10.

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

## Data refresh / R2

GitHub Actions builds and validates new datasets before publication. Published datasets are immutable. Latest-pointer objects select the active dataset. A failed build must never replace the previous good pointer.

The production R2 lifecycle policy was manually inspected and confirmed OK on 2026-08-16:

- `datasets/` → 30-day historical retention
- `metrics/` → 30-day historical retention
- `pointers/` → protected from the historical expiration rule
- incomplete multipart uploads → 7-day cleanup

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
| 10 | World-class Screener + Stock Research UI/UX | 🟡 Release candidate |

## Phase 9 closure

Phase 9 completed the final production acceptance checkpoint. The production smoke suite passed readiness, liveness, health, metadata, screener queries, search/sort, stock detail, chart horizons, CSV export, 400/404 contracts, CORS and frontend reachability. The smoke test was hardened to handle Render cold starts correctly.

## Phase 10 closure gate

Phase 10 is complete in source but remains a release candidate until the latest `main` commit is deployed successfully to Vercel and the user performs the final desktop/mobile Screener and individual-stock UI/UX acceptance pass.

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
- `docs/NEXT_AUDIT.md` — Phase 8 closure and Phase 9/10 handoff
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
- `docs/PHASE10_UI_UX.md` — Phase 10 UI/UX release candidate and acceptance gate
- `docs/HANDOVER_PROMPT.md` — continuation prompt for future AI sessions
