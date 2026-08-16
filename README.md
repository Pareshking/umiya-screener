# Umiya Screener V2

A performance-first, API-driven NSE quantitative momentum screener and stock research interface.

> **Current status: Phases 0–10 complete; production-ready source is on `main`.**

## Production

- Frontend: https://pareshpatel.vercel.app/
- API: https://umiya-screener-api.onrender.com/
- API docs: https://umiya-screener-api.onrender.com/docs
- Health: `/api/v1/health`
- Liveness: `/api/v1/live`
- Readiness: `/api/v1/ready`

## Product

Umiya V2 is intentionally a modern web research product rather than a Streamlit port.

### Screener

- dense, table-first ranked results;
- server-side search, filtering, sorting and pagination;
- structured filter drawer with Universe, Momentum, Trend, Risk/Participation and Data Quality groups;
- quick screens, active filter chips and Clear all;
- explicit X/Clear search control;
- sticky headers, column visibility and CSV export;
- responsive mobile result cards and bottom navigation;
- prepared quantitative metrics only; no market-wide calculations in the browser.

### Stock research

- compact stock identity and signal header;
- adjusted-close price chart with range selector and pointer inspection;
- Momentum section with 1M/3M/6M/9M/12M returns and acceleration;
- Risk & Trend section with Sharpe, R², 52W proximity, EMA 200 and volume ratio;
- Relative & Data Context section with industry-relative strength, persistence and provenance;
- responsive desktop/tablet/mobile layout;
- duplicate metric representations removed.

## Architecture

```text
Official NSE constituents
        ↓
Yahoo Finance Adjusted Close + Volume
        ↓
Validated 10-year dataset
        ↓
Offline quantitative metrics
        ↓
Cloudflare R2 immutable datasets + latest pointers
        ↓
FastAPI on Render
        ↓ JSON/HTTP
Next.js on Vercel
```

The frontend never performs market-wide financial calculations. User filtering, search, sorting and pagination operate on prepared analytical data through the API.

## Canonical data contract

Production market data is:

- Yahoo Finance Adjusted Close
- Yahoo Finance Volume
- last 10 years from build date
- common market `as_of`
- minimum 126 genuine observations
- maximum 3-calendar-day freshness
- independent price/volume freshness validation

For the canonical V2 price matrix, missing observations are forward-filled only after each stock's first genuine observation. Values before first observation are never fabricated.

Momentum windows are 21/63/126/189/252 trading days. A missing longer window remains unavailable; available component weights are renormalized rather than assigning an artificial zero.

ATR and other High/Low-dependent metrics are deliberately excluded because OHLC is outside the current data contract.

## API

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

## Data refresh / publication

GitHub Actions builds and validates new datasets before publication. Published datasets are immutable. Latest-pointer objects select the active dataset. A failed build never replaces the previous good pointer.

Production R2 lifecycle/retention was manually verified on 2026-08-16:

- historical `datasets/` → 30-day retention;
- historical `metrics/` → 30-day retention;
- `pointers/` → protected;
- incomplete multipart uploads → 7-day cleanup.

## Phase history

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture / guardrails | Complete |
| 1 | Data foundation | Complete |
| 2 | Quantitative engine | Complete |
| 3 | Query API + Screener UX | Complete |
| 4 | Stock detail + charts | Complete |
| 5 | Production deployment / hardening | Complete |
| 6 | Measurement / correctness / performance | Complete |
| 7 | Operational hardening | Complete |
| 8 | Edge-case audit / Screener evolution | Complete |
| 9 | Production release & acceptance | Complete |
| 10 | World-class Screener + Stock Research UI/UX | **Complete** |

## Working rules

- Do not reintroduce Streamlit architecture or rerun-style behaviour.
- Do not move financial calculations into React/TypeScript.
- Do not download market data in response to UI filters/search.
- Do not use ephemeral API-local storage as the production source of truth.
- Do not display invented/demo market data in production.
- Preserve the validated quantitative methodology.
- Keep pipeline, quant engine, API and frontend independently testable.
- Update implementation, tests and documentation together for contract changes.

## Documentation map

- `docs/PROJECT_CONTEXT.md` — current context and guardrails
- `docs/ARCHITECTURE.md` — system boundaries and data flow
- `docs/PHASE_STATUS.md` — phase state
- `docs/PHASE10_UI_UX.md` — Phase 10 completion record
- `docs/DATA_CONTRACT.md` — canonical data/freshness rules
- `docs/QUANT_METHODLOGY.md` — quantitative calculation contract
- `docs/OPERATIONS_RUNBOOK.md` — deployment/refresh/recovery
- `docs/VALIDATION.md` — test and production validation strategy
