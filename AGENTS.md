# Umiya Screener V2 — Agent Guardrails

Read this file before changing code.

## Mission

Build a fast, professional quantitative research platform. The first production module is the Screener. The old `Pareshking/Umiya` repository is reference-only.

## Absolute rules

1. Do not modify or use the old Streamlit architecture as the template for V2.
2. Do not put financial calculations in the Next.js frontend.
3. Do not download market data or rebuild market-wide metrics because a user changes a filter/sort/search/page.
4. The FastAPI service is a read/query layer over a published analytical dataset; it is not a market-data worker.
5. Never use fake/demo financial values as a production fallback.
6. Heavy data acquisition and metric calculation belongs in the independent pipeline (`scripts/build_data.py`, `scripts/build_metrics.py`, or their successors).
7. Production analytical data must use durable shared storage and atomic publication; API-local ephemeral disk is not a production data architecture.
8. Preserve quantitative methodology only after verifying the old implementation. Preserve formulas/requirements, not Streamlit implementation details.
9. Every important metric must be deterministic, documented, testable without network access, and protected against look-ahead/data-alignment errors.
10. Measure performance before introducing complexity. The target is fast query interaction over prepared data, not merely a faster-looking UI.
11. Mobile is a first-class UX target.
12. Keep API contracts independent of Pandas/Parquet implementation details.
13. Do not add future Umiya tabs until the Screener Definition of Done in README is substantially complete.
14. The canonical V2 market-data input is exactly **10 years of Yahoo Finance Adjusted Close + Volume**. Do not silently add Open/High/Low/unadjusted Close.
15. Use one common market as-of date. A stock is eligible only with >=126 valid Adjusted Close and Volume observations and a latest Adjusted Close no more than 3 calendar days behind that common date.
16. Weekends and exchange holidays are not missing data. Never manufacture trading rows.
17. A 12M RoC with insufficient history is defined as zero; do not invent another fallback without an explicit methodology decision.

## Before a significant change

Check `README.md`, especially:
- End goal
- Non-negotiable V2 principles
- Target architecture
- Definition of Done
- Roadmap
- Anti-drift working agreement

Also read `docs/DATA_POLICY.md` for market-data and missing-data decisions.

If a proposed change conflicts with those rules, redesign before coding.

## Validation expectation

After meaningful changes, run/verify:
- Python unit/engine/API tests as applicable
- Next.js production build
- data/schema tests where applicable
- live data smoke tests where applicable
- CI status

Do not claim a task is complete based only on code being committed.

## Source-of-truth hierarchy

1. Current user requirements and decisions
2. `README.md` V2 architecture and Definition of Done
3. `docs/DATA_POLICY.md`
4. Explicitly verified quantitative behaviour from old `Pareshking/Umiya`
5. Current implementation

When current implementation conflicts with the first four, fix the implementation.
