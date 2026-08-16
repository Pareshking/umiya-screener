# Validation and Audit Strategy

## Automated layers

### Unit

Deterministic tests for formulas, lookbacks, freshness, history eligibility and edge cases.

### Data

NSE 750 count, duplicates, missing symbols, common as-of date, freshness, history completeness and provenance.

### Quant

Metric calculations and symbol alignment against deterministic fixtures and real-data validation.

### API

Filtering, sorting, pagination, search, export, metadata, stock detail, charts and malformed requests.

### Frontend

Production Next.js build and deployed availability.

### Production smoke

`.github/workflows/production-smoke.yml` exercises the deployed Vercel/Render path.

## Current green gates

- Python validation: green
- Real NSE/Yahoo validation: green
- Frontend production build: green
- Production smoke: green

## Phase 6 live audit

The next validation layer is measurement rather than correctness-only testing.

Capture p50/p95 for:

1. initial frontend load
2. unfiltered query
3. numeric filter
4. multi-filter query
5. sort
6. search
7. stock detail
8. chart

Also test:

- mobile device UX
- Render cold start
- R2 bootstrap
- fresh data `as_of`
- APCOTEXIND injected-stock path

## Correctness rule

A fast wrong result is a failure. Performance work must not alter the quantitative contract without explicit validation.

## Production fallback rule

Never replace missing API/data with hard-coded/demo financial values. Show an explicit unavailable/error state.
