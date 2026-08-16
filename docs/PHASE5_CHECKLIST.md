# Phase 5 — Production Readiness Checklist

## Status

**Implementation complete. One final housekeeping item remains before formal Phase 5 closure.**

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

## Final remaining item

- [ ] **Verify/configure Cloudflare R2 object lifecycle/retention policy.**

The purpose is to prevent immutable historical datasets from accumulating indefinitely.

### Required lifecycle behaviour

- Apply retention/expiration to historical immutable dataset objects under `datasets/` and `metrics/`.
- Do **not** expire `pointers/` through the historical-data rule.
- Never delete the currently active/latest dataset while it is still current.
- Consider a 30-day initial retention period, subject to rollback needs.
- Configure cleanup for incomplete multipart uploads if appropriate.
- Verify the rule in the actual Cloudflare R2 bucket.

## Phase 5 closure condition

Phase 5 may be formally closed only after the actual R2 bucket lifecycle configuration is verified/configured and documented.

After that, Phase 6 begins. Do not treat Phase 6 performance/mobile work as Phase 5 blockers.
