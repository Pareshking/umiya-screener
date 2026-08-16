# Production Analytical Storage

## Decision

**Cloudflare R2 Standard** is the current target for production analytical dataset storage.

Why:

- S3-compatible API, so the Python worker can use standard S3 tooling.
- Designed for object storage, which matches versioned Parquet datasets.
- No egress bandwidth charge on R2.
- Current Standard free allowance includes 10 GB-month storage, 1 million Class A operations and 10 million Class B operations per month. See Cloudflare's current pricing documentation before production deployment.
- Keeps the storage layer independent from FastAPI and Next.js.

The expected Screener dataset is small enough that object storage is a better fit than introducing a database solely to hold the analytical files.

## Object layout

```text
umiya-screener/
  datasets/
    price-history/
      <dataset-version>/
        adj_close.parquet
        volume.parquet
        eligibility.parquet
        metadata.json
    metrics/
      <dataset-version>/
        screener_metrics.parquet
        metadata.json
  pointers/
    latest-price-history.json
    latest-metrics.json
```

## Publication protocol

The worker must never overwrite the active dataset in place.

```text
Build candidate locally
        ↓
Validate completely
        ↓
Upload immutable version
        ↓
Verify uploaded objects
        ↓
Atomically update latest pointer
        ↓
API reads pointer → active version
```

If a build fails, the pointer remains unchanged and the previous dataset continues serving.

## API behaviour

FastAPI reads the active version. It does not write market data and does not run the data acquisition pipeline.

The API may cache the downloaded analytical dataset in process memory for fast queries, but that cache is disposable. R2 remains the source of durable truth.

## Credentials

R2 credentials must exist only in worker/API server environment configuration. Never commit them, expose them to Next.js, or place them in client-side environment variables.

## Status

- Architecture decision: **selected**
- Code integration: pending production deployment phase
- Live bucket/credential validation: pending because deployment credentials are not yet configured
