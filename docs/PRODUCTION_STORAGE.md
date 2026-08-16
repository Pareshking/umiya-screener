# Production Analytical Storage

## Decision

**Cloudflare R2 Standard** is the production target and active durable store for published Screener analytical datasets.

Why:

- S3-compatible API, so the Python worker uses standard S3 tooling.
- Versioned Parquet datasets fit object storage well.
- Keeps durable analytical storage independent from FastAPI and Next.js.

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

The worker never overwrites the active dataset in place.

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

If a build fails, the pointer remains unchanged and the previous valid dataset continues serving.

## Lifecycle policy — verified in production

The active production R2 bucket has the following lifecycle configuration:

- `datasets/` historical immutable versions: **30-day retention**
- `metrics/` historical immutable versions: **30-day retention**
- `pointers/`: **protected from historical expiration**
- incomplete multipart uploads: **7-day cleanup**

The publication design keeps the active pointer target separate from historical retention, so lifecycle cleanup cannot remove the active pointer or the active published version during normal operation.

## API behaviour

FastAPI reads the active version. It does not acquire market data or rebuild the analytical dataset on user requests.

The API may cache the downloaded analytical dataset in process memory for fast queries, but that cache is disposable. R2 is the durable source of truth for published production data.

## Credentials

R2 credentials exist only in worker/API server environment configuration. They are never committed, exposed to Next.js, or placed in client-side environment variables.

## Validation record

- Real R2 publication: passed.
- Controlled production refresh: passed.
- Pointer advancement: passed.
- Post-publication production readiness smoke: passed.
- Lifecycle/retention configuration: verified.

See `docs/PHASE5_STATUS.md` and `docs/PHASE7_STATUS.md` for the production acceptance records.
