# Umiya Screener V2 — AI Handover Prompt

**Checkpoint:** 2026-08-16
**Repository:** `Pareshking/umiya-screener`
**Scope:** Screener only

Copy the prompt below into a new AI chat when continuing this project.

---

## HANDOVER PROMPT

You are taking over development of **Umiya Screener V2**. Work directly in the GitHub repository `Pareshking/umiya-screener` on `main` unless there is a specific reason to create a branch.

### 1. Read these documents first

Read, in this order:

1. `docs/PROJECT_CONTEXT.md` — authoritative project context and guardrails.
2. `docs/PHASE_STATUS.md` — current phase state.
3. `docs/NEXT_AUDIT.md` — immediate pending work.
4. `docs/ARCHITECTURE.md` — system architecture.
5. `docs/DATA_CONTRACT.md` and `docs/DATA_POLICY.md` — canonical data rules.
6. `docs/PRODUCTION_STORAGE.md` — R2 publication/storage design.
7. `docs/DEPLOYMENT.md` and `docs/OPERATIONS_RUNBOOK.md` — deployment/operations.
8. `docs/QUANT_METHODLOGY.md` and `docs/QUANT_METHODS.md` — quantitative methodology.
9. `docs/PRODUCTION_AUDIT.md` — production audit findings.
10. `docs/PHASE5_STATUS.md` and `docs/PHASE5_CHECKLIST.md` — Phase 5 closure state.

Do not rely on this prompt alone if a repository document contains a more specific contract.

### 2. Current architecture

The production architecture is:

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

Frontend interactions must never trigger a market-wide rebuild. Financial calculations belong in the backend/data pipeline.

Production URLs:

- Frontend: `https://pareshpatel.vercel.app/`
- API: `https://umiya-screener-api.onrender.com/`
- API docs: `https://umiya-screener-api.onrender.com/docs`

### 3. What has just been fixed

The latest hardening pass addressed:

- dynamic NSE constituent-count handling instead of brittle exact-750 assumptions;
- catastrophic incomplete-universe detection;
- Yahoo Adj Close + Volume coverage validation;
- independent price and volume freshness validation;
- cache TTL/staleness handling;
- immutable R2 dataset publication and pointer validation;
- safe R2 bootstrap/download validation;
- corrupt/incomplete dataset rejection;
- stale frontend stock/chart request cancellation;
- production smoke tests no longer depending on one hard-coded stock;
- regression fixtures aligned with the price+volume eligibility contract;
- R2 pointer JSON contract consistency;
- insufficient long-lookback returns remain unavailable rather than being fabricated as 0%.

Do not undo these protections merely to restore an old test or simplify code.

### 4. Latest validation checkpoint

Commit:

`05cea11ccf2e975e96aea3ff5293384e2d584f27`

The validation run for that checkpoint passed:

- **50 Python tests passed**
- **frontend build passed**
- **10-year Yahoo Adj Close + Volume validation passed**
- **real current-universe Phase 2 metric validation passed**
- **production smoke passed**

The latest documentation commits are subsequent documentation-only commits. If CI is running because of those documentation changes, wait for the latest run before making assumptions about regressions.

### 5. Immediate pending item — do this first

**Do not start Phase 6 yet.**

First verify/configure the actual Cloudflare R2 lifecycle/retention policy.

Recommended starting configuration:

```text
datasets/ historical immutable versions → 30 days
metrics/  historical immutable versions → 30 days
pointers/                                  → do not expire
incomplete multipart uploads               → abort after 7 days
```

30 days is only a proposed starting value. Confirm the desired rollback window before applying it.

This must be checked in the **actual R2 bucket**, not inferred from repository code.

After verification:

1. record the actual final retention policy in the repository;
2. update `docs/PHASE5_STATUS.md`, `docs/NEXT_AUDIT.md`, and `docs/PHASE_STATUS.md`;
3. formally close Phase 5;
4. only then begin Phase 6.

### 6. Phase 6 starting plan

Phase 6 is **measurement first, optimization second**.

Measure the deployed application in this order:

1. initial frontend load;
2. unfiltered screener query;
3. single numeric filter;
4. multi-filter query;
5. sort/search;
6. stock detail;
7. chart loading;
8. p50/p95 latency for each;
9. mobile UX and rendering;
10. Render cold start;
11. R2 bootstrap/hydration latency;
12. dataset freshness/as-of correctness.

Only optimise bottlenecks supported by measurements. Do not redesign the architecture simply because a different stack might be theoretically faster.

### 7. Data contract — do not violate

Canonical market data is:

- Yahoo Finance **Adjusted Close**
- Yahoo Finance **Volume**
- 10-year history
- common market `as_of`
- minimum 126 valid observations
- maximum 3 calendar days of freshness
- price and volume freshness checked separately

No High/Low/OHLC should be introduced silently. If a future metric needs OHLC, make an explicit data-contract decision and update documentation/tests.

Missing long-history data must stay missing. Never manufacture 0% returns for unavailable periods.

### 8. Universe policy

The project is conceptually an NSE 750 screener, but **do not hard-code the current live universe to exactly 750 rows**.

Official constituent-count changes are allowed. The pipeline should detect catastrophic incompleteness but tolerate legitimate constituent-count changes.

Never weaken the safety floor merely because Yahoo/NSE temporarily returns fewer stocks.

### 9. APCOTEXIND rule

`APCOTEXIND.NS` is a test fixture used to verify newly appearing constituents can pass the pipeline.

It is **not** a production frontend stock test.

Do not add it permanently to the canonical NSE universe and do not alter production data just to make it visible in the UI.

### 10. Storage/publication rules

Datasets are immutable.

The latest-pointer object selects the active dataset. Publication must upload and validate the immutable dataset before advancing the pointer.

If a new build fails, the previous good pointer must remain usable.

Do not replace this with ad-hoc mutable files.

### 11. Performance rules

The original problem with Streamlit was repeated work on user interactions. The V2 design exists specifically to avoid that.

Do not put expensive calculations into React/Next.js.

Do not rebuild the full NSE universe when a user changes a filter.

The expected fast path is:

```text
cached/versioned metrics
→ API filter/sort/search
→ small JSON response
→ frontend render
```

### 12. Testing rules

Before declaring a change complete:

- run Python tests;
- run frontend build;
- run relevant data-contract tests;
- run production smoke when production-facing behavior changes;
- inspect GitHub Actions results rather than assuming success.

If CI fails, obtain the actual artifact/log and fix the underlying issue. Do not modify a test only to make CI green unless the test itself contradicts the current documented contract.

### 13. Important repository boundaries

Do not:

- modify the old `Pareshking/Umiya` repository;
- reintroduce Streamlit;
- add future tabs before Screener quality is established;
- use fake financial data;
- put financial calculations in the frontend;
- optimise without measurement;
- weaken data validation;
- silently change the quantitative methodology;
- silently change the data contract.

### 14. How to work

Start by checking the current `main` HEAD and current GitHub Actions status.

Then read the documents listed above.

Then perform the **R2 lifecycle verification**, because that is the only known Phase 5 closure gate.

Do not immediately start coding Phase 6.

If the R2 lifecycle gate is already verified by the time you start, confirm that from repository documentation/evidence and then begin the Phase 6 measurement plan.

For any code change, first understand the existing implementation and tests. Prefer small, targeted fixes over broad rewrites.

When changing a contract, update the implementation, regression tests, and the relevant documentation together.

At the end of every meaningful task, update the appropriate project-status document so the next AI session can continue without reconstructing history from chat logs.

---

## End of handover prompt
