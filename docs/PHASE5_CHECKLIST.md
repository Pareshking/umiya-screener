# Phase 5 — Production Readiness Checklist

## Implementation complete

- [x] Free-first deployment architecture documented
- [x] Scheduled weekday data-refresh workflow added
- [x] Manual refresh dispatch supported
- [x] Immutable R2 publication path wired
- [x] Price + screener-metrics datasets published independently
- [x] Validation required before pointer publication
- [x] Previous good dataset preserved on failed build
- [x] Runtime API can hydrate latest metrics from R2
- [x] Runtime stock charts can hydrate latest price history from R2
- [x] Production FastAPI container added
- [x] Render deployment blueprint present
- [x] Vercel Next.js configuration present
- [x] Production CORS configurable through environment
- [x] Deployment secrets/configuration documented

## Requires connected production accounts

- [x] Configure production R2 secrets in GitHub Actions
- [ ] Run first real scheduled/manual R2 publication
- [ ] Deploy FastAPI to Render
- [ ] Deploy Next.js to Vercel
- [ ] Set `NEXT_PUBLIC_API_URL` to the deployed API
- [ ] Set production `ALLOWED_ORIGINS` to the Vercel origin
- [ ] Live smoke test
- [ ] Measure deployed p50/p95 query latency
- [ ] Verify mobile UX on real device
- [ ] Verify stock-detail deep links
- [ ] Verify failure/stale-data states
