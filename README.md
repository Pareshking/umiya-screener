# Umiya Screener

A clean rebuild of the Umiya NSE quantitative screener. The existing `Pareshking/Umiya` repository is reference-only and is never modified by this project.

## Architecture

```text
Next.js frontend
      ↓ JSON/HTTP
FastAPI API
      ↓
Persistent + in-memory metric cache
      ↓
Python quantitative engine + data loaders
      ↓
Official NSE index constituents + Yahoo Finance OHLCV
```

The expensive market-wide calculation is performed only when the metric cache is missing/stale or an explicit refresh is requested. Normal filter, sort and pagination requests operate on the prepared metric table instead of rerunning the complete application.

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
- Persistent Parquet metric cache
- Responsive desktop table + mobile stock cards

## Local development

### Backend

```bash
pip install -r requirements.txt
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

The frontend contains a small demo dataset fallback, so the UI remains inspectable before the backend has finished its first market-data build.

## Deployment target

- Frontend: Vercel / Next.js
- Backend: Render / FastAPI

`render.yaml` contains the backend service definition.

## Validation

GitHub Actions validates both the Python engine and the Next.js production build on pushes and pull requests.

## Reference project

`Pareshking/Umiya` is used only to reproduce and validate quantitative methodology and existing product behavior. It must not be modified by this project.

## Disclaimer

For research and educational use only. Not financial or investment advice.
