# Umiya Screener V2

A clean, performance-first rebuild of the Umiya NSE quantitative screener.

**The old `Pareshking/Umiya` repository is reference-only. Never modify it as part of this project.** It is used for quantitative methodology, validated formulas, existing research requirements, and product behaviour—not as an architectural template.

## End goal

Build a **professional, fast, mobile-first quantitative research screener** for the NSE 750 universe that feels like a modern research terminal rather than a Streamlit application.

The finished product must provide professional desktop/mobile UX, fast interactions over prepared data, reproducible calculations, transparent methodology, reliable data handling, strong validation, and an architecture that can later support RRG, breadth, portfolio and other Umiya modules without redesigning the foundation.

**Immediate scope: Screener only.** Do not add other tabs until Screener is production-quality.

---

# 1. Non-negotiable V2 principles

### Clean rebuild — not a Streamlit conversion

We are rebuilding around a new architecture. Preserve useful quantitative methodology and product requirements, but do not port the old UI architecture.

### No Streamlit baggage

Do NOT carry forward Streamlit architecture, reruns, session-state patterns, UI-triggered Python execution, UI-triggered downloads, Streamlit caching/workarounds, old page/view structure, old mobile limitations, old styling, or performance compromises created by Streamlit.

The old application is a **reference implementation, not a migration target**.

### UI never owns calculations

Next.js renders and interacts with data through APIs. Financial calculations belong in the Python quantitative layer.

### User interaction never rebuilds the market

Changing a filter, sort, page, column, or search term must NOT download data, rebuild the NSE 750 dataset, recalculate market-wide indicators, or execute the complete Python pipeline.

### Data pipeline and API are separate

```text
Official NSE constituent sources
          ↓
Market-data acquisition
          ↓
Quantitative calculations
          ↓
Validated analytical dataset
          ↓
Durable shared storage
          ↓
FastAPI read-only query service
          ↓ JSON/HTTP
Next.js frontend
```

The API must be able to start and serve the latest valid dataset without downloading or rebuilding the market.

### No fake financial data

Production UI must never silently display hard-coded/demo stock prices, rankings, returns or market indicators. If API/data is unavailable, show an explicit unavailable/error state. Demo fixtures are allowed only in isolated development tests, never as a production fallback.

### Preserve methodology, not implementation

Re-implement and validate useful old Umiya calculations in clean, testable modules rather than blindly copying UI-coupled code. Every important metric should have a documented definition, inputs, lookback, formula/convention, minimum history, missing-data behaviour and look-ahead-bias policy.

### Performance is a product requirement

The architecture exists partly to solve the old several-second Streamlit interaction problem. Engineering targets:

| Interaction | Target |
|---|---:|
| Existing-result sort | <100–200 ms |
| Filter over prepared dataset | <200–500 ms |
| Search | <200 ms |
| Column/display change | near instant |
| Cached stock detail | <500 ms |
| Heavy calculation | background/offline; never UI-blocking |

These are targets, not guarantees. Measure real deployed p50/p95 performance.

---

# 2. Target architecture

```text
                         UMIYA SCREENER V2

 ┌──────────────────────────────────────────────────────┐
 │                DATA / COMPUTE LAYER                  │
 │                                                      │
 │  NSE constituent files + Yahoo/market data           │
 │                     ↓                                │
 │            Data acquisition layer                    │
 │                     ↓                                │
 │            Quantitative engine                       │
 │                     ↓                                │
 │       Validation / quality / versioning              │
 │                     ↓                                │
 │         Analytical dataset (Parquet/Arrow)           │
 └─────────────────────┬────────────────────────────────┘
                       ↓
                Durable shared storage
                       ↓
 ┌──────────────────────────────────────────────────────┐
 │                    FASTAPI                           │
 │  Read-only query/service layer                       │
 │  Filtering / sorting / pagination / metadata         │
 │  Stock-detail queries / health / dataset status      │
 └─────────────────────┬────────────────────────────────┘
                       ↓ JSON/HTTP
 ┌──────────────────────────────────────────────────────┐
 │                    NEXT.JS                           │
 │  Desktop terminal UX / Mobile-first UX               │
 │  Tables / cards / filters / search / charts           │
 │  Loading / error / empty states                      │
 └──────────────────────────────────────────────────────┘
```

Technology direction:

- Frontend: Next.js + TypeScript
- UI: Tailwind/shadcn-style component architecture
- Backend: FastAPI + Python
- Quantitative engine: NumPy/Pandas initially; optimize only when measurement justifies it
- Analytical storage: Parquet/Arrow initially; implementation must remain replaceable
- Data source: official NSE constituent files + Yahoo Finance OHLCV
- Frontend target: Vercel
- Backend target: Render or equivalent
- Data pipeline: independent scheduled worker/job
- Production dataset: durable shared storage, not ephemeral API-local disk

Do not introduce technology for fashion. Choose based on performance, reliability, maintainability and cost.

---

# 3. Canonical NSE 750 universe

The research universe is the combination of these five official constituent files:

1. Nifty 50 — 50
2. Nifty Next 50 — 50
3. Nifty Midcap 150 — 150
4. Nifty Smallcap 250 — 250
5. Nifty Microcap 250 — 250

Intended total: **750 stocks**.

Preserve source files separately and retain `Index` membership. Do not blindly truncate a larger universe to 750. Handle duplicates explicitly and expose source/count diagnostics.

```text
https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv
https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv
https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv
https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv
https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv
```

---

# 4. Quantitative scope

The screener should support the methodology established in Umiya while keeping every metric independently testable.

### Momentum

- 1M, 3M, 6M, 9M, 12M returns
- cross-sectional momentum score
- momentum acceleration

### Risk-adjusted momentum

- 3M Sharpe
- 6M Sharpe
- defined lookback volatility inputs

### Trend

- 50 / 100 / 200 EMA
- price distance from each EMA
- 52-week-high distance
- within-20%-of-52-week-high condition

### Trend quality / structure

- 1Y R²
- persistence
- ATR / ATR %
- ATR stop / Chandelier-style diagnostics where specified

### Volume

- volume ratio and validated volume diagnostics

### Relative strength

- industry-relative momentum
- industry-level context where defined

### Universe metadata

- symbol
- company name
- industry
- index membership
- current price
- data-quality/status fields where applicable

**Do not invent formulas merely because a metric name exists. Document and test the exact definition.**

---

# 5. Calculation integrity rules

Every calculation must:

1. Avoid look-ahead bias.
2. Use clearly defined trading-day/lookback conventions.
3. Handle insufficient history explicitly.
4. Handle missing/invalid prices and volumes explicitly.
5. Avoid silent divide-by-zero behaviour.
6. Preserve symbol alignment.
7. Be deterministic for the same input/configuration.
8. Be unit-testable without network access.
9. Be separated from API/UI code.
10. Have synthetic/reference tests for important formulas.

Where old Umiya methodology differs from a textbook formula, preserve the Umiya methodology **only after verifying what the original code actually does**.

---

# 6. Analytical dataset / data pipeline

The expensive calculation is an explicit pipeline:

```bash
python scripts/build_metrics.py
```

It should:

1. Load/validate the five NSE constituent sets.
2. Acquire required OHLCV history.
3. Validate data quality.
4. Calculate required metrics.
5. Validate metric completeness/ranges.
6. Produce the analytical dataset.
7. Publish atomically to durable storage.
8. Record build timestamp/version/configuration.
9. Make the newly validated dataset available to the API.

The API consumes the latest valid published dataset.

**Production must not rely on an ephemeral local filesystem shared between unrelated services.** Storage must support durable persistence, atomic publication, worker/API access, rollback/recovery, and dataset version/provenance.

---

# 7. API contract

Initial endpoint family:

```text
GET  /api/v1/health
GET  /api/v1/screener/metadata
POST /api/v1/screener/query
GET  /api/v1/stocks/{symbol}
GET  /api/v1/stocks/{symbol}/chart
```

The query API should support universe/index filters, industry filters, numeric comparisons, multi-value filters, sorting, pagination, metadata and deterministic results.

The API is a **query/service layer, not a calculation notebook**. Never expose internal Pandas/Parquet details as the public contract.

---

# 8. Frontend product direction

The UI should behave like a **professional quantitative research terminal**, not a form-heavy data app.

### Desktop

Dense but readable research table, useful headers, fast sorting, powerful filter builder, active-filter chips, column selection, search, export, and later saved screens/quick view.

### Mobile

Mobile is first-class, not a collapsed desktop table. Use stock cards, compact high-value metrics, filter drawer, touch-friendly controls, responsive layouts, and avoid making horizontal scrolling the primary experience.

### Required UI states

Every data-driven component must handle:

- loading
- success
- empty result
- unavailable dataset/API
- API error
- stale dataset warning where applicable

Never mask an API failure with invented market data.

---

# 9. Validation strategy

### A — Unit tests

Synthetic deterministic tests for individual quantitative formulas.

### B — Engine tests

Complete metric calculations and multi-symbol alignment.

### C — Dataset tests

Universe count, duplicates, missing symbols/history, metric completeness, impossible/extreme values, provenance.

### D — API tests

Filtering, sorting, pagination, metadata, unavailable dataset, malformed requests, deterministic responses.

### E — Frontend build

Every push/PR validates the production Next.js build.

### F — Live smoke test

After deployment test health, metadata, initial query, filter, sort, pagination, stock detail and API failure behaviour.

### G — Performance

Measure real deployed initial page load, unfiltered query, numeric filter, multi-filter query, sort, search and stock detail. Record p50/p95 where practical.

---

# 10. Definition of Done — Screener

Do not call Screener V2 complete until these are true:

- [ ] Canonical NSE 750 verified
- [ ] Required metrics implemented
- [ ] Metric definitions documented
- [ ] Calculation reference tests pass
- [ ] No look-ahead/data-alignment issues found
- [ ] Analytical pipeline works independently of API/UI
- [ ] Dataset publication is atomic
- [ ] Durable production storage selected and tested
- [ ] API is read-only with respect to market-data calculation
- [ ] No user interaction triggers market-wide rebuild
- [ ] No fake/demo financial data in production UI
- [ ] Desktop UI complete
- [ ] Mobile UI complete
- [ ] Loading/error/empty/unavailable states complete
- [ ] API-driven frontend complete
- [ ] Filtering/sorting/pagination complete
- [ ] Stock detail complete
- [ ] Python CI green
- [ ] Next.js production build green
- [ ] Live NSE/Yahoo smoke test passes
- [ ] Deployed performance benchmark completed
- [ ] Performance materially better than old Streamlit interaction model
- [ ] Existing Umiya repo remains untouched

Only after this checklist is substantially complete should another Umiya module begin.

---

# 11. Roadmap

## Phase 0 — Architecture guardrails

Clean repo, no Streamlit, CI, engine/data/API/UI separation, architecture documentation.

## Phase 1 — Data foundation

NSE 750 loader, source validation, OHLCV acquisition, data-quality layer, analytical dataset, durable publication.

## Phase 2 — Quant engine

Implement/refactor metrics, document methodology, synthetic/reference tests, cross-sectional ranking, parity validation against old Umiya where appropriate.

## Phase 3 — Query API

Metadata, filters, sorting, pagination, stock detail, API tests.

## Phase 4 — Frontend

Desktop screener, mobile screener, filter builder, search, sort, columns, state handling.

## Phase 5 — Deployment

Vercel frontend, Render/equivalent API, scheduled data worker, durable storage, configuration, monitoring.

## Phase 6 — Real-world validation

Live data smoke test, calculation sanity checks, response-time benchmark, p50/p95 measurement, bottleneck fixes based on measurement.

## Phase 7 — Production hardening

Failure recovery, stale-data handling, dataset versioning, observability, security/rate limiting as appropriate, backup/recovery.

## Phase 8 — Future Umiya modules

Only after Screener is stable: RRG, market breadth, portfolio, and other research modules. Every future module must reuse the new foundation rather than reintroduce Streamlit-style coupling.

---

# 12. Explicitly prohibited

Do not:

- convert old Streamlit pages directly into React pages
- put financial calculations in React/TypeScript
- let filter widgets trigger Python market-wide calculations
- use Streamlit-style reruns
- rely on API-local ephemeral cache as production storage
- show fake stock data when the API fails
- optimise without benchmarks
- add every old tab before Screener is production-quality
- copy old code merely because it exists
- sacrifice mobile UX for desktop convenience
- sacrifice calculation correctness for UI speed
- sacrifice architecture for a quick demo

---

# 13. Relationship to old Umiya

`Pareshking/Umiya` remains untouched.

Use it to answer:

- What was the previous formula?
- What metrics existed?
- What filters existed?
- What product behaviour should be preserved?
- What outputs can be used for parity testing?

Do **not** use it as evidence that the new architecture should behave the same way internally.

```text
OLD UMIYA
   │
   ├── Quantitative knowledge ───────► preserve / validate
   ├── Product requirements ─────────► preserve where desired
   └── Streamlit implementation ─────► leave behind

                         ↓

                  UMIYA SCREENER V2
                  clean architecture
                  independent pipeline
                  fast API
                  professional UI
```

---

# 14. Anti-drift working agreement

Before a significant architectural change, ask:

1. Does it preserve clean V2 architecture?
2. Does it keep calculations independent from UI?
3. Does it keep interactions fast?
4. Does it avoid bringing Streamlit limitations back in another form?
5. Is the data pipeline independent from the API?
6. Is it testable and reproducible?
7. Does it move toward Definition of Done?
8. Are we solving a measured problem rather than adding unnecessary complexity?

If any answer is no, stop and redesign before coding.

**The end goal is NOT “a Streamlit app rebuilt in Next.js.”**

**The end goal is a fast, reliable, professional quantitative research platform whose first production module is the Umiya Screener.**

---

## Disclaimer

For research and educational use only. Not financial or investment advice.
