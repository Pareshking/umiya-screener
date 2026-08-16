# Phase 5 — Production Readiness Checklist

## Status

**COMPLETE — 2026-08-16**

### Verified

- [x] Free-first deployment architecture documented
- [x] Scheduled weekday data-refresh workflow added
- [x] Manual refresh dispatch supported
- [x] Immutable R2 publication path wired
- [x] Validation required before pointer publication
- [x] Previous good dataset preserved on failed build
- [x] Production R2 credentials configured
- [x] Real R2 publication completed successfully
- [x] FastAPI production service deployed/configured on Render
- [x] Next.js production deployment completed on Vercel
- [x] Production API URL configured
- [x] Production CORS configured/restricted
- [x] Fresh API runtime can hydrate published data from R2
- [x] Public health endpoint verified
- [x] Stock detail verified
- [x] Stock chart verified
- [x] CSV export verified
- [x] Real NSE 750/Yahoo validation green
- [x] Frontend production build green
- [x] Production smoke workflow green
- [x] Search/filter/sort/query path verified
- [x] API error handling verified
- [x] Cloudflare R2 lifecycle/retention policy configured and verified
- [x] Controlled real data refresh completed successfully
- [x] Post-publication production readiness smoke passed

### Final lifecycle policy

- `datasets/` → 30-day historical retention
- `metrics/` → 30-day historical retention
- `pointers/` → protected from the historical expiration rule
- incomplete multipart uploads → 7-day cleanup

The active/latest pointer is protected by the publication design and is not subject to the historical dataset expiration rule.

## APCOTEXIND clarification

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture. **It is not intended to be shown in the production frontend.** Do not describe it as a frontend end-to-end stock test or modify the canonical NSE 750 solely to display it.

## Phase 5 closure condition

All Phase 5 conditions are satisfied. Phase 5 is formally closed. Continue with the active phase documented in `docs/PHASE_STATUS.md`.
