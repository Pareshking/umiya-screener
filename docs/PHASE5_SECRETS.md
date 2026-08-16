# Phase 5 — GitHub R2 Secrets

The production refresh workflow expects these repository Actions secrets:

- `S3_ENDPOINT_URL` — Cloudflare R2 S3 endpoint
- `S3_BUCKET` — production R2 bucket name
- `S3_ACCESS_KEY_ID` — R2 S3 access key ID
- `S3_SECRET_ACCESS_KEY` — R2 S3 secret access key

Never commit these values to the repository or place them in source files. The workflow injects them only at runtime.
