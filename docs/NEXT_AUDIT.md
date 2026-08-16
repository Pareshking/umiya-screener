# Next Audit — Phase 6 Handoff

Phase 5 production smoke is green. Do not repeat the completed deployment checklist unless a regression occurs.

## Phase 6 execution order

1. Measure Vercel initial page/load behaviour.
2. Measure Render API health and cold-start behaviour.
3. Measure screener query p50/p95.
4. Measure numeric filter p50/p95.
5. Measure multi-filter p50/p95.
6. Measure sort and search p50/p95.
7. Measure stock-detail and chart latency.
8. Test real-device mobile UX.
9. Test APCOTEXIND newly-injected-stock flow end-to-end.
10. Validate data freshness/as-of presentation.
11. Identify the actual bottleneck.
12. Optimise only the bottleneck and rerun the same measurements.

## Phase 7 handoff

After Phase 6, address:

- R2 lifecycle/retention
- deeper failed-refresh recovery tests
- observability/alerts
- stale-data operational policy

No new Umiya modules before Screener production quality is established.
