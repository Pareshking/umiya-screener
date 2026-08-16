# Umiya Screener

A clean rebuild of the Umiya NSE quantitative screener. The existing `Pareshking/Umiya` repository is reference-only and is never modified by this project.

## Architecture

```text
Next.js frontend
      ↓ JSON/HTTP
FastAPI API
      ↓
Cached screener metric store
      ↓
Python quantitative engine + data loaders
      ↓
NSE / Yahoo Finance
```

The expensive market-wide calculation is performed once per backend refresh and retained in memory. Normal filter, sort and pagination requests operate on the prepared metric table instead of rerunning the complete application.

## Current scope

- NSE Total Market / deterministic NSE-750 working universe
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
- Fast API-side filtering, sorting and pagination
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
