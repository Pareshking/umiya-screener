# Umiya Screener V2 Architecture

## System boundary

```text
NSE constituent files + market data
              |
              v
      Data acquisition layer
              |
              v
      Quantitative engine
              |
              v
  Validation + dataset publication
              |
              v
     Durable analytical store
              |
              v
        FastAPI query API
              |
              v
         Next.js frontend
```

## Responsibility boundaries

### Data pipeline

Owns network access to market data, constituent refresh, data cleaning, metric calculation, quality validation, dataset versioning and atomic publication.

Must be runnable independently of the API and frontend.

### Quantitative engine

Pure/reproducible functions wherever practical. No HTTP, UI, Streamlit, or deployment concerns. Network-free tests use deterministic fixtures.

### Analytical dataset

Contains prepared fields needed for screener queries. It is a published product of the pipeline, not a UI cache. A dataset should carry build time/version/configuration/provenance metadata.

### FastAPI

Reads the latest valid dataset and serves query results. It owns request validation, filter semantics, sorting, pagination, metadata and stock-detail access. It must not trigger a full market rebuild.

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

## Build path

```text
Scheduled worker
      |
      +--> refresh NSE universe
      +--> acquire OHLCV
      +--> calculate metrics
      +--> validate dataset
      +--> write versioned temporary dataset
      +--> run integrity checks
      +--> atomically publish
      |
      v
Latest valid dataset
```

A failed build must not destroy the last known-good dataset.

## Storage evolution

Start with Parquet/Arrow because the universe is small and analytical. Keep the storage abstraction replaceable. If measurements later show that concurrent query volume, dataset size, or multi-user requirements justify DuckDB/PostgreSQL/another engine, change the storage implementation behind the API contract rather than redesigning the frontend.

## Performance philosophy

Do not optimize the old Streamlit execution model. Replace it.

The expensive work happens before user interaction. User requests should be dominated by filtering, serialization and network/render latency. Performance claims must be measured on the deployed system.

## Security and reliability direction

- No market-data credentials in the frontend.
- Secrets only in server/worker environment configuration.
- Validate and bound filter inputs.
- Rate limiting/authentication can be added without changing the quant engine.
- Never replace stale/unavailable data with fabricated values.
- Preserve last known-good dataset when a refresh fails.
