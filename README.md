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
 │  NSE constituent files + Yahoo Finance               │
 │                     ↓                                │
 │       10y Adjusted Close + Volume acquisition        │
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
- Market data: Yahoo Finance **Adjusted Close + Volume only**
- Constituent data: official NSE index files
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

Important V2 data rule: the canonical source provides only Adjusted Close and Volume. Metrics such as ATR that require High/Low are **not considered part of the Phase 1 data contract** and must be explicitly redesigned or justified during Phase 2 before being implemented.

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

### Phase 1 data foundation

The canonical data build is:

```bash
python scripts/build_data.py
```

It:

1. Loads/validates the five NSE constituent sets.
2. Requires exactly 750 unique symbols.
3. Acquires the last 10 years of Yahoo Finance Adjusted Close + Volume.
4. Determines one common market `as_of` date.
5. Applies the 126-valid-observation minimum.
6. Applies the maximum 3-calendar-day freshness rule.
7. Validates volume history for eligible stocks.
8. Writes Parquet data plus provenance metadata.
9. Publishes atomically through a `LATEST.json` pointer.

The Phase 1 build is deliberately independent of FastAPI and the frontend. It does **not** perform Phase 2 screener calculations.

### Phase 2 analytical pipeline

The expensive metric calculation will later be:

```bash
python scripts/build_metrics.py
```

It consumes the validated Phase 1 dataset, calculates the documented screener metrics, validates them, and publishes the analytical dataset for the API.

**Production must not rely on an ephemeral local filesystem shared between unrelated services.** Production storage must support durable persistence, atomic publication, worker/API access, rollback/recovery, and dataset version/provenance.

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

Synthetic deterministic tests for individual quantitative formulas and data-policy rules.

### B — Engine tests

Complete metric calculations and multi-symbol alignment.

### C — Dataset tests

Universe count, duplicates, missing symbols/history, common as-of date, 3-day freshness, metric completeness, impossible/extreme values, provenance.

### D — API tests

Filtering, sorting, pagination, metadata, unavailable dataset, malformed requests, deterministic responses.

### E — Frontend build

Every push/PR validates the production Next.js build.

### F — Live data smoke test

The Phase 1 CI test downloads the real NSE 750 universe and exact 10-year Yahoo window and records symbol-level history/missing-data diagnostics.

### G — Performance

Measure real deployed initial page load, unfiltered query, numeric filter, multi-filter query, sort, search and stock detail. Record p50/p95 where practical.

---

# 10. Definition of Done — Phase 0 + Phase 1

Phase 0 is complete when:

- [x] Clean V2 repository established
- [x] No Streamlit architecture dependency
- [x] README/architecture/agent guardrails documented
- [x] Data/quant/API/frontend responsibility boundaries defined
- [x] CI runs Python tests and Next.js production build
- [x] Old Umiya repository remains untouched

Phase 1 is complete when:

- [x] Canonical NSE 750 source definition established
- [x] NSE browser-like session/user-agent acquisition implemented
- [x] NSE HTML/block response detection implemented
- [x] Cached constituent fallback implemented with warnings
- [x] Canonical Yahoo data contract = Adjusted Close + Volume
- [x] Historical window = exact last 10 years from build date
- [x] Common market as-of date defined
- [x] Minimum 126 valid observations defined
- [x] Maximum 3-calendar-day freshness defined
- [x] Weekend/holiday handling defined
- [x] Partial-stock missing data handling defined
- [x] 12M RoC fallback decision recorded for Phase 2
- [x] Phase 1 standalone data-build script added
- [x] Atomic local dataset publication added
- [x] Provenance metadata added
- [x] Synthetic data-policy tests added
- [x] Real NSE 750 / Yahoo 10-year test completed successfully
- [ ] CI green after the latest data-foundation changes
- [ ] Production durable shared storage selected and tested

Phase 2 begins only after the remaining Phase 1 validation items above are resolved.

---

# 11. Roadmap

## Phase 0 — Architecture guardrails

Clean repo, no Streamlit, CI, engine/data/API/UI separation, architecture documentation. **Status: complete.**

## Phase 1 — Data foundation

NSE 750 loader, source validation, 10-year Adj Close + Volume acquisition, data-quality layer, standalone data build, atomic local publication and provenance. **Status: final validation in progress.**

## Phase 2 — Quant engine

Implement/refactor metrics against the canonical Adj Close + Volume contract, document methodology, synthetic/reference tests, cross-sectional ranking, parity validation against old Umiya where appropriate.

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
- silently add OHLCV fields to the canonical data contract

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
9. Does it respect the canonical 10-year Adjusted Close + Volume data contract?

If any answer is no, stop and redesign before coding.

**The end goal is NOT “a Streamlit app rebuilt in Next.js.”**

**The end goal is a fast, reliable, professional quantitative research platform whose first production module is the Umiya Screener.**

---

## Disclaimer

For research and educational use only. Not financial or investment advice.
