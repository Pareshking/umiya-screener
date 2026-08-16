# Umiya Screener V2 — Deployment

## Current production topology

```text
Vercel (Next.js frontend)
        ↓ HTTPS
Render (FastAPI API)
        ↓ read-only
Cloudflare R2 (durable immutable datasets)
        ↑
GitHub Actions refresh + validation
        ↑
Yahoo Finance + official NSE constituents
```

### Production URLs

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `https://umiya-screener-api.onrender.com/docs`

The frontend never downloads Yahoo/NSE data directly.

## Responsibilities

### Vercel

Hosts the stateless Next.js frontend. No market-data credentials.

### Render

Hosts FastAPI and serves the latest validated analytical dataset. It must not rebuild the NSE 750 market dataset because a user opens the site or changes a filter.

### GitHub Actions

Runs validation and the scheduled refresh. It builds the canonical datasets and publishes only validated immutable versions.

### Cloudflare R2

Stores immutable dataset versions and latest-pointer objects. It is the durable production source for published analytical data.

## Required secrets

GitHub Actions repository secrets:

- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET`

The API may use the same S3-compatible environment variables for runtime hydration, with `S3_REGION=auto` where required.

No credential belongs in source control or the frontend.

## Publication safety

```text
Build
 ↓
Validate
 ↓
Upload immutable dataset
 ↓
Advance latest pointer
```

Pointer advancement happens only after successful publication. Failed builds preserve the previous good dataset.

## Workflows

- `.github/workflows/data-refresh.yml` — scheduled/manual production dataset refresh.
- `.github/workflows/production-smoke.yml` — deployed API/frontend smoke audit.
- `.github/workflows/tests.yml` — repository validation/build tests.

## Phase 5 result

Production deployment, R2 publication/runtime hydration, CORS, health, query, export, stock detail, charts, error handling and production smoke have been verified.

## Phase 6 work

The following are intentionally deferred to Phase 6/7:

- detailed p50/p95 benchmark
- real-device mobile audit
- extended stale-data/failure recovery tests
- R2 lifecycle/retention audit
- deeper observability

These are no longer Phase 5 deployment blockers.
