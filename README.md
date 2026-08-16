# Umiya Screener

A clean rebuild of the Umiya NSE quantitative screener. The existing `Pareshking/Umiya` repository is reference-only and is never modified by this project.

## Architecture

```text
Scheduled/offline data pipeline
      ↓
Precomputed analytical dataset (Parquet)
      ↓
FastAPI read-only query service
      ↓ JSON/HTTP
Next.js frontend
```

The API process never downloads market data and never performs a market-wide metric rebuild because a user opened the page or changed a filter. Dataset construction is an explicit offline pipeline operation (`scripts/build_metrics.py`). This separation is intentional and is a core performance requirement of V2.

## Canonical NSE 750 universe

The screener uses the five official NSE Indices constituent files supplied for this project:

- Nifty 50 — 50
- Nifty Next 50 — 50
- Nifty Midcap 150 — 150
- Nifty Smallcap 250 — 250
- Nifty Microcap 250 — 250

The sources are stored separately and combined with an `Index` membership column. Symbols are de-duplicated rather than blindly truncating the resulting table to 750. Source-count diagnostics are exposed by `/api/v1/screener/metadata`.

## Current scope

- Canonical NSE 750 working universe
- Daily OHLCV data
- 1M / 3M / 6M / 9M / 12M momentum windows
- Risk-adjusted momentum and cross-sectional score
- 52-week-high proximity
- 50 / 100 / 200 EMA trend metrics
- 3M / 6M Sharpe
- 1Y R²
- Momentum acceleration
- Industry-relative momentum
- ATR, persistence and volume diagnostics
- Index / industry filtering
- Fast API-side filtering, sorting and pagination
- Persistent analytical dataset
- Responsive desktop table + mobile stock cards
- Explicit loading, unavailable-dataset and empty-result states

## Data pipeline

Build the analytical dataset from the repository root:

```bash
python scripts/build_metrics.py
```

This is a data-pipeline operation, not an API request. In production it should run on a scheduled worker and publish the resulting analytical dataset to durable shared storage accessible by the API service.

## Local development

### Backend

```bash
pip install -r requirements.txt
python scripts/build_metrics.py
uvicorn backend.app.main:app --reload --port 8000
```

API health: `http://localhost:8000/api/v1/health`

### Frontend

```bash
cd frontend
npm install
# create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000 if needed
npm run dev
```

Open `http://localhost:3000`.

The frontend does **not** contain fake market data. If the API/dataset is unavailable it displays an explicit unavailable/error state instead of presenting invented stock prices or rankings.

## Deployment target

- Frontend: Vercel / Next.js
- Backend: Render / FastAPI
- Data pipeline: separate scheduled worker
- Analytical dataset: durable shared storage (to be selected before production deployment)

`render.yaml` contains the current backend service definition. Production deployment is deliberately not considered complete until the data-pipeline storage path is durable and shared between the worker and API.

## Validation

GitHub Actions validates both the Python engine and the Next.js production build on pushes and pull requests.

## Reference project

`Pareshking/Umiya` is used only to reproduce and validate quantitative methodology and existing product requirements. Streamlit architecture, rerun behavior, UI-specific caching, and other implementation limitations from the old application are not carried into this project.

## Disclaimer

For research and educational use only. Not financial or investment advice.
