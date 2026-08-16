# Umiya Screener

A standalone NSE equity screener built as a clean successor to the existing Umiya terminal. The existing `Pareshking/Umiya` repository is reference-only and is never modified by this project.

## Scope

- NSE Total Market / NSE 750-style universe support
- Daily OHLCV data pipeline
- Multi-window momentum ranking: 1M, 3M, 6M, 9M, 12M
- Risk-adjusted momentum using return and volatility
- 52-week-high proximity filter
- 50/100/200 EMA trend filters
- Momentum acceleration
- Industry-relative momentum
- ATR and persistence diagnostics
- CSV export from the Streamlit screener
- Unit tests for quantitative calculations

## Design principles

1. No look-ahead bias.
2. Explicit handling of insufficient history and missing data.
3. Vectorized calculations wherever practical.
4. Data acquisition and quantitative calculations remain separate.
5. The old Umiya repository is read-only reference material.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Disclaimer

For research and educational use only. Not financial or investment advice.
