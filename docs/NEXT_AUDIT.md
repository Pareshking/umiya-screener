# Next Audit / Handover — 2026-08-16

## Current checkpoint

Phase 5 implementation and automated validation are complete. The only unresolved Phase 5 item is **external R2 lifecycle verification/configuration**.

Latest code-hardening checkpoint before documentation updates:

`05cea11ccf2e975e96aea3ff5293384e2d584f27`

Automated validation passed:

- 50 Python tests
- frontend build
- 10-year Yahoo Adj Close + Volume test
- real current-universe Phase 2 metric build
- production smoke

## Immediate next action

Verify the actual Cloudflare R2 bucket lifecycle rules.

Recommended starting configuration:

```text
Historical immutable datasets:
  datasets/ → 30 days
  metrics/  → 30 days

Do not expire through this rule:
  pointers/

Incomplete multipart uploads:
  abort after 7 days
```

The 30-day value is a recommendation, not a verified production setting. Confirm the rollback requirement before applying it.

## Verification checklist

- [ ] Open the actual production R2 bucket.
- [ ] Inspect Object Lifecycle Rules.
- [ ] Confirm historical `datasets/` retention.
- [ ] Confirm historical `metrics/` retention.
- [ ] Confirm `pointers/` is not accidentally covered.
- [ ] Confirm the active/latest dataset cannot be deleted while current.
- [ ] Confirm incomplete multipart-upload cleanup.
- [ ] Configure/fix the rule if needed.
- [ ] Save and re-check the final configuration.
- [ ] Record the final retention period in this repository.
- [ ] Then formally close Phase 5.

## Phase 6 after closure

Do not redesign first. Measure the deployed system first:

1. frontend initial load
2. unfiltered query
3. numeric filter
4. multi-filter
5. sort/search
6. stock detail/chart
7. p50/p95 latency
8. mobile UX
9. Render cold start/R2 bootstrap
10. data freshness/as-of correctness

Only optimise a measured bottleneck.

## Important constraints

- Screener-only scope for now.
- No Streamlit.
- No frontend financial calculations.
- No fake financial data.
- No hard-coded assumption that the current NSE universe must equal exactly 750 rows.
- Adj Close + Volume remains the canonical data contract unless explicitly changed.
- Never turn unavailable long-history returns into artificial 0% values.
- APCOTEXIND is a test fixture, not a production frontend stock.
- Do not weaken tests/validation to make CI pass.
