# Phase 10 — World-Class Screener UI/UX

**Status: RELEASE CANDIDATE — latest source ready; final Vercel deployment + human acceptance pending**

Updated: 2026-08-16

Phase 10 is the product-facing UI/UX phase after production acceptance. The goal is to make Umiya a substantially better research website than the original Streamlit application while preserving the existing quantitative engine, API contracts and data methodology.

## Release-candidate work completed

### Screener

- refreshed visual system with stronger hierarchy, spacing, typography and interaction states;
- balanced desktop KPI layout;
- clearer filter cards and active-filter chips;
- sticky table headers and improved row scanning;
- refined search, sort, column and export controls;
- responsive tablet behavior;
- purpose-built mobile result cards instead of forcing the desktop table onto a phone;
- mobile filter drawer and bottom navigation;
- clearer loading, empty, error and degraded states;
- keyboard-visible focus states and improved interaction affordances.

### Individual stock research page

- redesigned stock identity/hero area;
- prominent momentum rank, momentum score, CMP and 12-month return signals;
- explicit trend status relative to the 200 EMA;
- larger research-oriented adjusted-close chart with range selector;
- dedicated Momentum & Returns section;
- dedicated Technical Structure section;
- separated Research Context / dataset provenance;
- clearer desktop hierarchy and card composition;
- mobile-responsive research layout;
- back-to-Screener and research actions;
- consistent visual language with the Screener.

## Architecture guardrails

The UI work does **not** change:

- quantitative methodology;
- server-side calculations;
- API contracts;
- server-side filtering/search/sort/pagination;
- canonical Adj Close + Volume data contract;
- R2 publication/storage architecture;
- Vercel/Render deployment architecture.

## Current deployment evidence

Vercel deployment capacity has recovered. A deployment shown in the Vercel dashboard reached **Ready** in 26 seconds, but it was for the older `431feb7` commit (`fix: allow Vercel install without lockfile`). It is therefore **not** the final Phase 10 UI build.

The current `main` branch contains later Phase 10 UI/UX work. The remaining deployment gate is to deploy the latest `main` commit successfully once, then perform the real browser/device acceptance pass.

The earlier Vercel `build-rate-limit` condition should no longer be treated as an active blocker, but the successful older deployment must not be confused with the current release candidate.

## Validation already completed

- production API smoke passed for the latest stock-page commit;
- frontend source changes are committed to `main`;
- stock-page and Screener styles are present in the production frontend source;
- Phase 5–9 production/data/security gates remain the baseline.

## Final acceptance checklist

1. Deploy the latest `main` commit to Vercel.
2. Confirm deployment is **Ready**.
3. Open the latest deployed URL and verify the current Phase 10 source is actually served.
4. Desktop Screener review.
5. Mobile Screener review.
6. Desktop individual-stock review.
7. Mobile individual-stock review.
8. Test filter/search/sort/pagination/export.
9. Open several stock pages and switch chart ranges.
10. Verify loading/error/empty/degraded states.
11. Confirm no visual regressions from the previous production release.
12. Collect user feedback and make any final polish changes required.
13. Update this document and `docs/PHASE_STATUS.md` to **COMPLETE** only after the above evidence exists.

## Product principle

The original Streamlit application is the baseline to beat, not the design to copy. Phase 10 succeeds only when Umiya feels like a purpose-built quantitative research product: fast, clear, dense without being cluttered, and pleasant to use on both desktop and mobile.
