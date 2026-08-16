# R2 Production Runbook

1. Confirm repository Actions secrets: `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`.
2. Run `scheduled-data-refresh` manually from GitHub Actions on `main`.
3. Require build, tests, Yahoo validation and metrics validation to pass.
4. Verify `datasets/`, `metrics/`, and `pointers/` appear in the R2 bucket.
5. Verify latest pointer objects identify the newly published immutable datasets.
