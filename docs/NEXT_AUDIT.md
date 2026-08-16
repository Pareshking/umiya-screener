# Phase 6 — Production Measurement Plan

**Started:** 2026-08-16

Phase 5 is closed. The production R2 lifecycle policy has been configured and verified:

- `datasets/` → 30-day expiration
- `metrics/` → 30-day expiration
- `pointers/` → no expiration rule
- incomplete multipart uploads → 7-day abort

## Phase 6 objective

Measure the deployed system before changing architecture. The first goal is to identify the actual bottleneck in the Vercel → Render → R2/API path.

## Automated benchmark

Use:

- `scripts/phase6_benchmark.py`
- `.github/workflows/phase6-benchmark.yml`

The benchmark measures repeated production HTTP timings for:

1. screener query
2. numeric filter
3. multi-filter
4. search
5. sort
6. CSV export
7. stock detail
8. 3M chart
9. 6M chart
10. 1Y chart
11. frontend HTTP response

It reports p50, p95 and max latency and uploads raw measurements as a GitHub Actions artifact.

Run the workflow manually from GitHub Actions before making performance changes.

## Remaining Phase 6 work

- [ ] Run first benchmark and record baseline p50/p95.
- [ ] Separate Render cold-start from warm-request latency.
- [ ] Measure R2 bootstrap separately where practical.
- [ ] Measure real browser/mobile experience (HTTP benchmark is not a substitute for browser UX).
- [ ] Verify data freshness/as-of display.
- [ ] Run APCOTEXIND as a controlled injected-stock pipeline test without changing the canonical production universe.
- [ ] Identify the largest measured bottleneck.
- [ ] Make only targeted optimisation(s).
- [ ] Repeat benchmark and compare before/after.

## Constraints

- Screener-only scope.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- Do not force the live universe to exactly 750 rows.
- Adj Close + Volume remains the canonical data contract.
- Do not turn unavailable long-history returns into artificial 0% values.
- Do not optimise without measurements.
