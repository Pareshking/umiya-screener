# Umiya Screener V2 Architecture

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

## Canonical market-data contract

The V2 Screener uses **only**:

- `adj_close` — Yahoo Finance Adjusted Close; primary price series for return, trend and ranking calculations.
- `volume` — Yahoo Finance Volume; used for volume-based diagnostics.

The historical window is the **last 10 years from the build date**. We do not download Yahoo's entire available history for production.

Open, High, Low and unadjusted Close are not part of the canonical V2 dataset. A future metric that genuinely requires another field must be an explicit methodology decision and must not silently expand the contract.

## Responsibility boundaries

### Data pipeline

Owns network access to market data, constituent refresh, data cleaning, common market as-of determination, 126-observation eligibility, 3-calendar-day freshness validation, metric calculation, quality validation, dataset versioning and atomic publication.

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
      +--> acquire 10y Adj Close + Volume
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

## Phase 1 data build

The canonical data-foundation build is:

```bash
python scripts/build_data.py
```

It is deliberately independent of the API and Phase 2 metric calculations. It validates the NSE-750 universe, downloads the ten-year Adjusted Close + Volume dataset, applies the common-as-of/126-observation/3-day freshness rules, writes provenance metadata, and publishes the dataset through an atomic `LATEST.json` pointer.

## Storage evolution

Start with Parquet/Arrow because the universe is small and analytical. Keep the storage abstraction replaceable. If measurements later show that concurrent query volume, dataset size, or multi-user requirements justify DuckDB/PostgreSQL/another engine, change the storage implementation behind the API contract rather than redesigning the frontend.

The repository's local publication mechanism is an engineering foundation. Production must use durable shared storage; that deployment choice is intentionally tracked separately from the Phase 1 code path.

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
