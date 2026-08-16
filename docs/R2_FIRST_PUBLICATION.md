# First R2 Publication

1. Confirm GitHub repository secrets exist: `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`.
2. Open GitHub Actions → `scheduled-data-refresh`.
3. Select **Run workflow** on `main`.
4. Wait for build, metric generation, tests, and R2 publication to complete.
5. Verify the R2 bucket contains `datasets/`, `metrics/`, and `pointers/` objects.
6. Do not manually upload or modify published dataset objects; publication is immutable and the pointer selects the latest validated dataset.
