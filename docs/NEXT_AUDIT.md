# Next production audit execution

The repository now contains `scripts/production_smoke.py` and the scheduled `.github/workflows/production-smoke.yml`.

1. Deploy the latest `main` commit to Render so the restrictive production CORS default is live.
2. Run the `production-smoke` workflow manually from GitHub Actions (or wait for its weekday schedule).
3. Require health `dataset_ready: true`, metadata universe `750`, filtered query, search/sort, CSV export, stock detail, 3M/6M/1Y chart, CORS, 404/400 handling, and frontend HTTP 200 to pass.
4. Record the script's query p50/p95 latency output.
5. After a fresh Render restart, repeat health and the first chart request to verify R2 bootstrap.
6. Verify the scheduled data-refresh workflow continues to validate before publishing and that a failed refresh leaves the previous pointer untouched.
7. Configure and verify an R2 lifecycle policy for old immutable dataset versions; do not delete the active pointer target.
8. Test a production stock-detail deep-link refresh on mobile and desktop.
9. When these gates pass, mark Phase 5 complete and begin Phase 6; no new product features before then.
