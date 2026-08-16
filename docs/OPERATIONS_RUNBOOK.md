# Production Operations Runbook

## Services

Frontend: `https://pareshpatel.vercel.app/`

API: `https://umiya-screener-api.onrender.com/`

API health: `/api/v1/health`

## Deploy flow

```text
GitHub main
   ├─ Vercel → Next.js frontend
   └─ Render → FastAPI backend
```

The frontend receives the production API URL through its environment configuration. Render production CORS must include the Vercel origin.

## Data refresh flow

GitHub Actions workflow: `scheduled-data-refresh`

1. Build NSE 750 data.
2. Download/validate Yahoo 10Y Adj Close + Volume.
3. Build metrics.
4. Run validation.
5. Publish immutable datasets to Cloudflare R2.
6. Update latest pointers only after successful publication.

If a refresh fails, do not manually delete or replace the last good pointer.

## R2 secrets

GitHub Actions repository secrets:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Never commit credentials. Never put them in frontend environment variables.

## R2 lifecycle / retention — manually verified

The Cloudflare R2 production bucket lifecycle configuration was manually inspected and confirmed **OK on 2026-08-16**.

Expected production policy:

- `datasets/` → 30-day historical retention
- `metrics/` → 30-day historical retention
- `pointers/` → protected from the historical expiration rule
- incomplete multipart uploads → 7-day cleanup

This is a manual production-console verification, not an automated repository check.

## Runtime recovery

If Render restarts, the API should bootstrap the latest published dataset from R2. A restart must not require a local rebuild of the market.

Check:

```text
GET /api/v1/health
GET /api/v1/screener/metadata
```

Expected healthy state includes `status=ok` and `dataset_ready=true`.

## Production smoke

Workflow: `.github/workflows/production-smoke.yml`

It validates:

- health
- metadata
- screener query
- search/sort
- export
- stock detail
- chart ranges
- CORS
- 400/404 handling
- frontend availability
- query latency

## If smoke fails

1. Identify the failing endpoint/step.
2. Check Render logs if the API is involved.
3. Check Vercel deployment/build if frontend is involved.
4. Check R2 pointer and object availability if dataset hydration is involved.
5. Do not mask the failure with fallback financial data.
6. Fix the root cause and rerun CI/smoke.

## APCOTEXIND test

Use `APCOTEXIND.NS` as the newly-injected-stock test case. The expected proof is:

```text
Yahoo
 → ingestion
 → validation
 → metrics
 → R2
 → Render API
 → Vercel UI
```

Do not add it permanently to production merely to make the UI show it.

## Phase 6 performance procedure

Measure before optimising:

- frontend initial load
- screener query
- filter
- multi-filter
- sort
- search
- stock detail
- chart

Record p50/p95 and identify the slowest layer.
