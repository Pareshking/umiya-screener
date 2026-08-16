# Phase 10 — World-Class Screener UI/UX

**Status: RELEASE CANDIDATE — awaiting Vercel deployment**

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

## Validation already completed

- production API smoke passed for the latest stock-page commit;
- frontend source changes are committed to `main`;
- stock-page and Screener styles are present in the production frontend source;
- Phase 5–9 production/data/security gates remain the baseline.

## Remaining release gate

The current GitHub/Vercel status reports `build-rate-limit` for the Vercel deployment. This is a Vercel account/project deployment-capacity limitation, not a reported Next.js application build failure.

Do not repeatedly trigger rebuilds while rate-limited. Once the rate limit clears, deploy the latest `main` commit once and perform the final real-browser acceptance pass.

## Final acceptance checklist

1. Vercel deploy succeeds for latest `main`.
2. Desktop Screener review.
3. Mobile Screener review.
4. Desktop individual-stock review.
5. Mobile individual-stock review.
6. Test filter/search/sort/pagination/export.
7. Open several stock pages and switch chart ranges.
8. Verify loading/error/empty states.
9. Confirm no visual regressions from the previous production release.
10. Update this document and `docs/PHASE_STATUS.md` to **COMPLETE** only after the above evidence exists.

## Product principle

The original Streamlit application is the baseline to beat, not the design to copy. Phase 10 succeeds only when Umiya feels like a purpose-built quantitative research product: fast, clear, dense without being cluttered, and pleasant to use on both desktop and mobile.
