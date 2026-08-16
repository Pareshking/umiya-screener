# Umiya Screener V2 — AI Handover Prompt

**Checkpoint:** 2026-08-16  
**Repository:** `Pareshking/umiya-screener`  
**Branch:** `main`  
**Scope:** Screener only  
**Current phase:** Phase 8 complete

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

**Phases 0–8 are complete.**

Phase 8 was an evidence-backed production Screener audit, not an architecture rewrite. It fixed concrete UX/correctness/resilience/API issues, added regression coverage, measured production behavior and synchronized the release documentation.

### 4. Phase 8 completed work

- stale-query race fixed with per-query `AbortController`;
- degraded/data-unavailable state separated from ordinary request errors;
- mobile filter search fixed;
- saved-screen restoration hardened;
- unsupported sorts now return HTTP 400;
- pagination boundaries and numeric equality coercion fixed;
- null/missing metrics remain unavailable;
- R2 pointer traversal/namespace validation added;
- repeated-refresh/idempotency regression coverage added;
- constituent replacement/membership-change regression coverage added;
- production payload sizes and repeated query latency measured;
- deployed API smoke passed after the latest Phase 8 code checkpoint;
- README, phase status, next-audit, audit and handover documents synchronized.

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

The project targets NSE 750, but **do not hard-code the live universe to exactly 750 rows**. Legitimate constituent-count changes and corporate-action/index membership changes are allowed. Catastrophic incompleteness must still be rejected.

### 7. APCOTEXIND rule

`APCOTEXIND.NS` is a data-pipeline/newly-injected-stock test fixture. It is **not a production frontend stock test**. Do not permanently add it to the production universe merely to make it visible in the UI.

### 8. Storage/publication rules

Datasets are immutable. The latest pointer selects the active dataset. Upload and validate the immutable dataset before advancing the pointer. If a new build fails, the previous good pointer must remain usable.

### 9. Performance rules

Do not put expensive financial calculations into React/Next.js. Do not rebuild the full universe when a user changes a filter.

Preferred fast path:

```text
versioned metrics → API filter/sort/search → small JSON → frontend render
```

Latest Phase 8 production smoke measured query p50 120 ms / p95 247 ms. Do not optimize further without new evidence.

### 10. Testing rules

Before declaring a future change complete:

- run Python tests;
- run frontend build when frontend code changes;
- run relevant data-contract tests;
- run production smoke when production-facing behavior changes;
- inspect actual GitHub Actions results.

### 11. Repository boundaries

Do not:

- modify the old `Pareshking/Umiya` repository;
- reintroduce Streamlit;
- add unrelated future tabs/modules without a concrete requirement;
- use fake financial data;
- put financial calculations in the frontend;
- optimize without measurement;
- weaken data validation;
- silently change quantitative methodology or data contract.

### 12. Next-work rule

Phase 8 is closed. Do not reopen the audit or redesign the application unless a new production defect, measured performance problem or explicit product requirement justifies it.

The repository cannot independently perform a human visual walkthrough on a real desktop/mobile browser/device; do not claim that observation was completed unless a human actually performs it.

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
