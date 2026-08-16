# Umiya Screener V2 — AI Handover Prompt

**Checkpoint:** 2026-08-16
**Repository:** `Pareshking/umiya-screener`
**Branch:** `main`
**Scope:** Screener only
**Current phase:** Phase 8

Copy the prompt below into a new AI chat when continuing this project.

---

## HANDOVER PROMPT

You are taking over development of **Umiya Screener V2**. Work directly in `Pareshking/umiya-screener` on `main` unless there is a specific reason to create a branch.

### 1. Read these documents first

Read in this order:

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
11. `docs/PHASE8_PLAN.md`

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

**Phases 0–7 are complete. Phase 8 is active.**

Phase 8 is an improvement/audit phase, not an architecture rewrite.

Start with **8A + 8B together**:

- production desktop/mobile UX audit;
- correctness and edge-case audit;
- fix concrete defects found;
- add regression tests;
- update documentation with the change.

Then proceed through 8C–8F as justified by findings.

### 4. Phase 5/6/7 important completed work

The production path now includes:

- immutable R2 datasets and latest pointers;
- R2 lifecycle: datasets 30 days, metrics 30 days, pointers protected, incomplete multipart uploads 7 days;
- dynamic constituent-count handling rather than exact-750 assumptions;
- catastrophic incomplete-universe detection;
- Adj Close + Volume coverage/freshness validation;
- price/volume freshness checked independently;
- cache TTL/staleness handling;
- safe R2 bootstrap/download validation;
- corrupt/incomplete dataset rejection;
- production readiness endpoints;
- request IDs and no-store API responses;
- explicit stale/degraded behavior;
- bounded API requests;
- security automation and CodeQL;
- production benchmark and latency work;
- corporate-action/index-count resilience;
- APCOTEXIND pipeline fixture;
- production smoke and controlled real refresh validation.

Do not undo these protections merely to simplify code or restore an old assumption.

### 5. Canonical data contract — do not violate

- Yahoo Finance **Adjusted Close**
- Yahoo Finance **Volume**
- 10-year history
- common market `as_of`
- minimum 126 valid observations
- maximum 3 calendar days freshness
- independent price/volume freshness checks

No High/Low/OHLC should be introduced silently.

Missing long-history data must remain missing. Never fabricate unavailable returns as 0%.

### 6. Universe policy

The project targets NSE 750, but **do not hard-code the live universe to exactly 750 rows**.

Legitimate constituent-count changes and corporate-action/index membership changes are allowed. Catastrophic incompleteness must still be rejected.

### 7. APCOTEXIND rule

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture.

It is **not a production frontend stock test**. Do not permanently add it to the production universe merely to make it visible in the UI.

### 8. Storage/publication rules

Datasets are immutable. The latest pointer selects the active dataset. Upload and validate the immutable dataset before advancing the pointer.

If a new build fails, the previous good pointer must remain usable.

Do not replace this with ad-hoc mutable files.

### 9. Performance rules

The V2 architecture exists to avoid Streamlit-style repeated market-wide computation.

Do not put expensive calculations into React/Next.js.

Do not rebuild the full universe when a user changes a filter.

Preferred fast path:

```text
versioned metrics → API filter/sort/search → small JSON → frontend render
```

### 10. Testing rules

Before declaring a change complete:

- run Python tests;
- run frontend build when frontend code changes;
- run relevant data-contract tests;
- run production smoke when production-facing behavior changes;
- inspect actual GitHub Actions results.

Do not modify tests solely to make CI green when the implementation violates the documented contract.

### 11. Repository boundaries

Do not:

- modify the old `Pareshking/Umiya` repository;
- reintroduce Streamlit;
- add unrelated future tabs/modules;
- use fake financial data;
- put financial calculations in the frontend;
- optimize without measurement;
- weaken data validation;
- silently change quantitative methodology or data contract.

### 12. How to work in Phase 8

Start by checking current `main` HEAD and GitHub Actions status.

Then read the Phase 8 documents and inspect the deployed frontend/API.

Do not immediately redesign anything.

For each defect:

1. reproduce it;
2. identify the root cause;
3. make the smallest appropriate fix;
4. add/adjust regression coverage;
5. run relevant tests/builds;
6. verify production if applicable;
7. update status documentation.

At the end of every meaningful task, update the appropriate project-status document so the next AI session can continue without reconstructing history from chat logs.

---

## End of handover prompt
