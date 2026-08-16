# Umiya Screener V2 — Deployment

## Free-first production target

The production goal is to run the public Screener with free-tier services wherever practical:

```text
Vercel (Next.js frontend)
        ↓ HTTPS
Render or equivalent free backend
        ↓ read-only
Cloudflare R2 (durable dataset)
        ↑
GitHub Actions scheduled data refresh
        ↑
Yahoo Finance + NSE constituent sources
```

The frontend must never download Yahoo/NSE data directly.

## Responsibilities

### Vercel

Hosts the Next.js frontend. It should remain stateless and contain no market-data credentials.

### API service

FastAPI serves the latest validated analytical dataset. It must not rebuild the NSE 750 market dataset because a user opened the site or changed a filter.

### GitHub Actions

Runs the data refresh on trading weekdays after the market closes and can also be started manually. It builds the canonical 10-year dataset, runs validation, and publishes only a successfully validated immutable version.

### Cloudflare R2

Stores immutable dataset versions and a small latest-version pointer. The API reads the latest valid version. R2 is object storage, not a calculation engine.

## Required secrets

GitHub Actions requires:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`

No credentials belong in the repository or frontend.

## Publication safety

The refresh workflow must follow:

```text
Download
  ↓
Build
  ↓
Validate
  ↓
Upload immutable version
  ↓
Publish latest pointer
```

If any step before publication fails, the existing latest pointer remains untouched.

The API therefore continues serving the last known-good dataset.

## Data schedule

The default workflow runs Monday-Friday at 19:00 IST (13:30 UTC). It can be manually dispatched for recovery/testing.

The schedule is intentionally after the Indian market session. A failed run should not cause a destructive update.

## Free-tier principle

Do not introduce a paid database, always-on worker, queue, or dedicated server merely to make the first production release work.

The analytical dataset is small enough that object storage plus a read-oriented API is sufficient for the initial public Screener.

If traffic or dataset/query requirements outgrow the free architecture, measure the bottleneck first and upgrade only the constrained component.

## Production checklist

- [ ] Vercel project connected to `frontend/`
- [ ] `NEXT_PUBLIC_API_URL` points to production API
- [ ] FastAPI service deployed from `render.yaml` or equivalent
- [ ] Durable R2 bucket created
- [ ] Four GitHub Actions R2 secrets configured
- [ ] Scheduled refresh run succeeds
- [ ] Immutable dataset appears in R2
- [ ] Latest pointer advances only after validation
- [ ] API can read the latest pointer
- [ ] API continues serving the previous version after a failed refresh
- [ ] CORS restricted to production frontend origin
- [ ] Health endpoint publicly reachable
- [ ] Live screener query succeeds
- [ ] Mobile and desktop smoke tests pass
- [ ] Real response-time benchmark recorded
