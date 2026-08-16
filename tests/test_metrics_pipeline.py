import numpy as np
import pandas as pd

import backend.app.service as service


def synthetic_phase1(days=320, symbols=("AAA", "BBB", "CCC")):
    index = pd.bdate_range("2025-01-01", periods=days)
    t = np.arange(days, dtype=float)
    close = pd.DataFrame({s: np.exp(np.log(100 + i * 10) + (0.004 + i * 0.0005) * t) for i, s in enumerate(symbols)}, index=index)
    volume = pd.DataFrame(100_000.0, index=index, columns=symbols)
    eligibility = pd.DataFrame({
        "Symbol": list(symbols),
        "History Days": [days] * len(symbols),
        "Last Price Date": [index[-1]] * len(symbols),
        "Data Age Days": [0] * len(symbols),
        "Volume Days": [days] * len(symbols),
        "Last Volume Date": [index[-1]] * len(symbols),
        "Volume Age Days": [0] * len(symbols),
    })
    universe = pd.DataFrame({
        "Symbol": list(symbols),
        "Company Name": [f"{s} Ltd" for s in symbols],
        "Industry": ["A", "A", "B"],
        "Index": ["NIFTY 50"] * len(symbols),
    })
    metadata = {"market_as_of": str(index[-1].date()), "schema_version": "1.1", "built_at_utc": "2026-08-16T00:00:00+00:00"}
    return close, volume, eligibility, universe, metadata


def test_build_metric_frame_composes_complete_screener_contract(monkeypatch):
    monkeypatch.setattr(service, "_load_phase1_dataset", lambda: synthetic_phase1())
    frame, built_at = service.build_metric_frame()

    assert len(frame) == 3
    required = {
        "Symbol", "Company Name", "Industry", "Index", "Momentum Score", "Rank",
        "1M Return", "3M Return", "6M Return", "9M Return", "12M Return",
        "3M Sharpe", "6M Sharpe", "R² 1Y", "Industry Relative", "Acceleration",
        "EMA 50", "EMA 100", "EMA 200", "52W High", "Volume Ratio",
        "Persistence 6M %", "Data Age Days", "Last Volume Date", "Volume Age Days", "Market As Of",
    }
    assert required.issubset(frame.columns)
    assert frame["Rank"].notna().all()
    assert frame["Symbol"].is_unique
    assert built_at.tzinfo is not None


def test_build_metric_frame_preserves_symbol_alignment(monkeypatch):
    monkeypatch.setattr(service, "_load_phase1_dataset", lambda: synthetic_phase1())
    frame, _ = service.build_metric_frame()
    assert list(frame["Symbol"]) == ["AAA", "BBB", "CCC"]
    assert frame.set_index("Symbol").loc["CCC", "Industry"] == "B"
