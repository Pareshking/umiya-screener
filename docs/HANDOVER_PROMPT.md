# Umiya Screener V2 — AI Handover Prompt

**Checkpoint:** 2026-08-16  
**Repository:** `Pareshking/umiya-screener`  
**Branch:** `main`  
**Scope:** Screener only  
**Current phase:** Phase 10 release candidate

Copy the prompt below into a new AI chat when continuing this project.

---

## HANDOVER PROMPT

You are taking over development of **Umiya Screener V2**. Work directly in `Pareshking/umiya-screener` on `main` unless there is a specific reason to create a branch.

### 1. Read these documents first

1. `docs/PROJECT_CONTEXT.md`
2. `docs/PHASE_STATUS.md`
3. `docs/NEXT_AUDIT.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DATA_CONTRACT.md` and `docs/DATA_POLICY.md`
6. `docs/PRODUCTION_STORAGE.md`
7. `docs/DEPLOYMENT.md` and `docs/OPERATIONS_RUNBOOK.md`
8. `docs/QUANT_METHODLOGY.md` and `docs/QUANT_METHODS.md`
9. `docs/PRODUCTION_AUDIT.md`
10. `docs/PHASE5_STATUS.md`, `docs/PHASE5_CHECKLIST.md`, `docs/PHASE6_STATUS.md`, `docs/PHASE7_STATUS.md`
11. `docs/PHASE8_PLAN.md` and `docs/PHASE8_AUDIT.md`
12. `docs/PHASE9_RELEASE.md` and `docs/PHASE10_UI_UX.md`

### 2. Current production architecture

```text
NSE constituent acquisition
        ↓
Yahoo Finance 10Y Adj Close + Volume
        ↓
Validation / eligibility
        ↓
Quant metrics
        ↓
Immutable versioned R2 datasets
        ↓
FastAPI on Render
        ↓
Next.js on Vercel
```

Production URLs:

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `https://umiya-screener-api.onrender.com/docs`

### 3. Phase status

**Phases 0–9 are complete. Phase 10 is a release candidate.**

Phase 10 is the product-facing UI/UX upgrade for both the Screener and individual stock research page. Source work is complete; final closure requires deployment of the latest `main` source to Vercel and human desktop/mobile acceptance.

### 4. Phase 10 completed work

- Screener visual hierarchy, spacing and typography refresh;
- KPI/filter/chip/table/search/sort/column/export polish;
- responsive tablet/mobile layouts;
- mobile result cards, filter drawer and bottom navigation;
- clearer loading, empty, error and degraded states;
- individual stock research hero and signal hierarchy;
- adjusted-close chart and range selector;
- Momentum & Returns section;
- Technical Structure section;
- Research Context / dataset provenance;
- responsive stock research layout;
- consistent visual language across Screener and stock page.

No quantitative methodology, API contract, server-side calculation or data architecture changes were introduced.

### 5. Current Vercel status

Vercel deployment capacity has recovered. A recent dashboard deployment reached **Ready** in 26 seconds, but it was the older `431feb7` commit (`fix: allow Vercel install without lockfile`). Do not use that deployment as the final Phase 10 UI review.

Deploy the latest `main` commit once. Confirm it reaches Ready, then verify that the deployed build contains the current Phase 10 source.

Do not repeatedly redeploy the old commit.

### 6. Canonical data contract — do not violate

- Yahoo Finance **Adjusted Close**
- Yahoo Finance **Volume**
- 10-year history
- common market `as_of`
- minimum 126 valid observations
- maximum 3 calendar days freshness
- independent price/volume freshness checks

No High/Low/OHLC should be introduced silently.

Missing long-history data must remain missing. Never fabricate unavailable returns as 0%.

### 7. Universe policy

The project targets NSE 750, but **do not hard-code the live universe to exactly 750 rows**. Legitimate constituent-count changes and corporate-action/index membership changes are allowed. Catastrophic incompleteness must still be rejected.

### 8. APCOTEXIND rule

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture. It is **not a production frontend stock test**. Do not permanently add it to the production universe merely to make it visible in the UI.

### 9. Storage/publication rules

Datasets are immutable. The latest pointer selects the active dataset. Upload and validate the immutable dataset before advancing the pointer. If a new build fails, the previous good pointer must remain usable.

The production R2 lifecycle policy was manually verified as OK on 2026-08-16: datasets and metrics retain historical versions for 30 days, pointers are protected, and incomplete multipart uploads are cleaned after 7 days.

### 10. Performance rules

Do not put expensive financial calculations into React/Next.js. Do not rebuild the full universe when a user changes a filter.

Preferred fast path:

```text
versioned metrics → API filter/sort/search → small JSON → frontend render
```

### 11. Testing rules

Before declaring a future change complete:

- run Python tests;
- run frontend build when frontend code changes;
- run relevant data-contract tests;
- run production smoke when production-facing behavior changes;
- inspect actual GitHub Actions results;
- for Phase 10, perform real browser/device review before claiming UI/UX completion.

### 12. Repository boundaries

Do not:

- modify the old `Pareshking/Umiya` repository;
- reintroduce Streamlit;
- add unrelated future tabs/modules without a concrete requirement;
- use fake financial data;
- put financial calculations in the frontend;
- optimize without measurement;
- weaken data validation;
- silently change quantitative methodology or data contract.

### 13. Phase 10 closure rule

Do not mark Phase 10 complete merely because source code and CI are green. The latest `main` source must first be deployed successfully to Vercel, and the user must perform a real desktop/mobile review of both the Screener and individual stock page. Any final changes should then be evidence-based and revalidated.

For future work:

1. inspect current `main` and GitHub Actions status;
2. identify the concrete requirement/defect;
3. make the smallest appropriate change;
4. add regression coverage;
5. run relevant tests/builds;
6. verify production when applicable;
7. update status documentation.

---

## End of handover prompt
