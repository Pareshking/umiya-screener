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

The current production workflow uses these GitHub Actions secrets:

- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET`

These are S3-compatible names because Cloudflare R2 is accessed through its S3 API. The API service uses the same `S3_*` environment variables, plus optional `S3_REGION=auto`.

No credentials belong in the repository or frontend.

## Publication safety

The refresh workflow follows:

```text
Download
  ↓
Build canonical price dataset
  ↓
Build screener metrics
  ↓
Validate
  ↓
Upload immutable version
  ↓
Publish latest pointer
```

The immutable dataset is uploaded before its latest pointer is advanced. If validation or an earlier publication step fails, the existing latest pointer remains untouched.

The API therefore continues serving the last known-good dataset.

## Data schedule

The current workflow runs Monday-Friday at 19:00 IST (13:30 UTC). It can also be manually dispatched for recovery/testing.

The schedule is intentionally after the Indian market session. A failed run should not cause a destructive update.

## Free-tier principle

Do not introduce a paid database, always-on worker, queue, or dedicated server merely to make the first production release work.

The analytical dataset is small enough that object storage plus a read-oriented API is sufficient for the initial public Screener.

If traffic or dataset/query requirements outgrow the free architecture, measure the bottleneck first and upgrade only the constrained component.

## Production checklist

### Verified

- [x] Vercel production deployment exists and latest deployment completed successfully
- [x] FastAPI production service is configured through `render.yaml`
- [x] Durable R2 publication path is implemented
- [x] GitHub Actions R2 credentials are configured (confirmed by successful publication run)
- [x] Manual scheduled refresh run succeeds
- [x] Canonical dataset build succeeds
- [x] Screener metric build succeeds
- [x] Generated datasets pass the refresh validation step
- [x] Immutable datasets are published to R2
- [x] Latest dataset pointers are advanced after successful validation/publication
- [x] Live screener query has been verified from the deployed application

### Still to verify

- [ ] `NEXT_PUBLIC_API_URL` points to the intended production API and is documented
- [ ] API can read the current R2 pointers from a fresh instance
- [ ] API continues serving the previous version after a deliberately failed refresh
- [ ] CORS is restricted to the production frontend origin
- [ ] Health endpoint publicly reachable and reports the expected dataset state
- [ ] Stock-detail endpoint and deep links work in production
- [ ] Chart endpoint works from a fresh API instance
- [ ] CSV export works in production
- [ ] Mobile smoke test on a real device
- [ ] Desktop smoke test
- [ ] Real p50/p95 response-time benchmark recorded
- [ ] Stale-data and unavailable-data UI states verified
