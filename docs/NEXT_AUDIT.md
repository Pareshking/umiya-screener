# Next production audit execution

1. Obtain the deployed FastAPI base URL from the Render service.
2. Run `python scripts/production_smoke.py <API_URL>`.
3. Verify health reports `dataset_ready: true`.
4. Force a cold start/restart of the API and repeat the smoke test.
5. Confirm the first chart request can bootstrap price data from the R2 latest-price pointer.
6. Restrict `ALLOWED_ORIGINS` to the production Vercel origin after confirming the live frontend works.
7. Measure query latency for metadata, default query, filtered query, and export.
8. Test `/stocks/{symbol}` and `/stocks/{symbol}/chart` from the production frontend.
9. Test mobile deep links and browser refresh on a stock-detail route.
10. Only after these pass, move to failure-recovery and operational monitoring.
