# Phase 5 — Production Readiness Checklist

## Verified

- [x] Free-first deployment architecture documented
- [x] Scheduled weekday data-refresh workflow added
- [x] Manual refresh dispatch supported
- [x] Immutable R2 publication path wired
- [x] Validation required before pointer publication
- [x] Previous good dataset preserved on failed build
- [x] Production R2 credentials confirmed by successful refresh
- [x] First real manual R2 publication completed successfully
- [x] FastAPI production service deployed/configured
- [x] Next.js production deployment completed successfully
- [x] Live screener query verified

## Remaining

- [ ] Verify `NEXT_PUBLIC_API_URL` is the intended production API URL
- [ ] Verify fresh API instance can bootstrap from R2 without local dataset
- [ ] Configure/verify production CORS is restricted to frontend origin
- [ ] Verify public health endpoint and dataset status
- [ ] Verify stock-detail deep links
- [ ] Verify stock chart endpoint from a fresh instance
- [ ] Verify CSV export in production
- [ ] Measure deployed p50/p95 query latency
- [ ] Verify mobile UX on a real device
- [ ] Verify desktop UX
- [ ] Verify failure/stale-data states
- [ ] Test previous-good-dataset recovery after a failed refresh
