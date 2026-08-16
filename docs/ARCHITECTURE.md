# Umiya Screener V2 Architecture

## Production topology

```text
GitHub Actions
  ├─ scheduled-data-refresh
  │    ├─ NSE constituents
  │    ├─ Yahoo 10Y Adj Close + Volume
  │    ├─ Phase 1 validation
  │    ├─ Phase 2 metrics
  │    ├─ tests
  │    └─ immutable R2 publication + latest pointers
  │
  └─ validation / production-smoke

Cloudflare R2
  ├─ immutable price datasets
  ├─ immutable metrics datasets
  └─ latest pointer objects

Render
  └─ FastAPI query service

Vercel
  └─ Next.js Screener UI
```

## System boundary

```text
NSE constituent files + Yahoo Finance
              |
              v
      Data acquisition layer
              |
              v
   Adjusted Close + Volume
              |
              v
      Quantitative engine
              |
              v
  Validation + immutable publication
              |
              v
        Cloudflare R2
              |
              v
        FastAPI on Render
              |
              v
        Next.js on Vercel
```

## Responsibility boundaries

### Data pipeline

Owns network access to market data, constituent refresh, data cleaning, common market as-of determination, 126-observation eligibility, 3-calendar-day freshness validation, metric calculation, quality validation, dataset versioning and publication.

Must run independently of the API and frontend.

### Quantitative engine

Pure/reproducible functions wherever practical. No HTTP, UI, Streamlit or deployment concerns. Network-free tests use deterministic fixtures.

### Analytical dataset

Contains prepared fields needed for screener queries. It is a published product of the pipeline, not a UI cache. It carries build/version/provenance information.

### Cloudflare R2

Durable shared source for published analytical data. Datasets are immutable. Latest-pointer objects activate a validated version. The pointer must never be advanced before the corresponding dataset is completely uploaded and validated.

### FastAPI

Reads the latest valid dataset and serves query results. It owns request validation, filter semantics, sorting, pagination, metadata, CSV export and stock-detail access. It must not trigger a full market rebuild.

### Next.js

Owns presentation, interaction state, responsive UX and API orchestration. It does not own quantitative definitions or market-wide calculations.

## Query path

```text
User changes filter
        |
        v
Next.js request
        |
        v
FastAPI validation
        |
        v
Prepared analytical dataset
        |
        v
Filter + sort + paginate
        |
        v
JSON response
        |
        v
Render result
```

There is intentionally no market-data download or full metric computation in this path.

## Refresh/publication path

```text
Scheduled GitHub Action
        |
        +--> refresh NSE universe
        +--> acquire 10y Adj Close + Volume
        +--> calculate metrics
        +--> validate
        +--> upload immutable version to R2
        +--> update latest pointer only after success
        |
        v
Latest valid dataset
```

A failed build must preserve the last known-good dataset.

## Canonical data contract

Phase 1 production data is Yahoo Finance Adjusted Close + Volume only. Historical window is the last 10 years from build date. Minimum eligible history is 126 valid observations and maximum freshness age is 3 calendar days.

Open/High/Low/unadjusted Close are not silently added. Any metric requiring them needs an explicit methodology/data-contract decision.

## Performance philosophy

The expensive work happens before user interaction. User requests should be dominated by filtering, serialization, network and rendering latency. Performance claims must be measured on the deployed system, not inferred from local development.

## Reliability

- No fake financial data in production.
- Missing data produces explicit unavailable/degraded states.
- Invalid requests are rejected.
- Unknown stocks return 404.
- Failed refreshes do not replace the last good pointer.
- API can bootstrap its latest dataset from durable R2 storage.
