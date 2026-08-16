from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def _price_frames(symbols: list[str], periods: int = 300):
    index = pd.date_range("2025-01-01", periods=periods, freq="B")
    close = pd.DataFrame(index=index, columns=symbols, dtype=float)
    volume = pd.DataFrame(index=index, columns=symbols, dtype=float)
    for i, symbol in enumerate(symbols):
        # Deterministic but non-identical paths; enough history for every Phase 2 window.
        trend = 100 + i * 10 + np.arange(periods) * (0.12 + i * 0.01)
        wave = np.sin(np.arange(periods) / (13 + i)) * (1.5 + i * 0.2)
        close[symbol] = trend + wave
        volume[symbol] = 100_000 + i * 10_000 + (np.arange(periods) % 17) * 1_000
    return close, volume, index[-1]


def test_phase1_accepts_injected_apcotexind(monkeypatch, tmp_path):
    """A newly appearing constituent must pass the Phase 1 contract without special-casing."""
    import scripts.build_data as build_data

    symbols = ["APCOTEXIND"] + [f"TEST{i:03d}" for i in range(749)]
    close, volume, as_of = _price_frames(symbols, periods=130)
    universe = pd.DataFrame(
        {
            "Symbol": symbols,
            "Company Name": ["Apcotex Industries Limited"] + symbols[1:],
            "Industry": ["Rubber Products"] + ["Synthetic Industry"] * 749,
            "Index": ["INJECTED_TEST"] + ["NIFTY_TEST"] * 749,
        }
    )
    universe.attrs["warnings"] = []
    universe.attrs["duplicate_symbols"] = []
    universe.attrs["source_counts"] = {"INJECTED_TEST": 1, "NIFTY_TEST": 749}

    monkeypatch.setattr(build_data, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(build_data, "load_universe", lambda: universe)
    monkeypatch.setattr(build_data, "fetch_prices", lambda requested: {"adj_close": close, "volume": volume})

    published, metadata = build_data.build()

    assert published.exists()
    assert metadata["universe_symbols"] == 750
    assert metadata["eligible_symbols"] == 750
    saved_close = pd.read_parquet(published / "adj_close.parquet")
    saved_volume = pd.read_parquet(published / "volume.parquet")
    saved_universe = pd.read_parquet(published / "universe.parquet")
    assert "APCOTEXIND" in saved_close.columns
    assert "APCOTEXIND" in saved_volume.columns
    assert "APCOTEXIND" in saved_universe["Symbol"].tolist()
    assert json.loads((tmp_path / "LATEST.json").read_text())["dataset"] == published.name


def test_phase2_metric_and_query_flow_accepts_injected_apcotexind(monkeypatch):
    """The injected stock must survive the metric builder and screener query contract."""
    import backend.app.service as service
    from backend.app.schemas import ScreenerQuery

    symbols = ["APCOTEXIND", "TEST001", "TEST002"]
    close, volume, as_of = _price_frames(symbols, periods=300)
    eligibility = pd.DataFrame(
        {
            "Symbol": symbols,
            "History Days": [300, 300, 300],
            "Last Price Date": [as_of] * 3,
            "Data Age Days": [0, 0, 0],
        }
    )
    universe = pd.DataFrame(
        {
            "Symbol": symbols,
            "Company Name": ["Apcotex Industries Limited", "Test One", "Test Two"],
            "Industry": ["Rubber Products", "Synthetic", "Synthetic"],
            "Index": ["INJECTED_TEST", "NIFTY_TEST", "NIFTY_TEST"],
        }
    )
    metadata = {"schema_version": "1.1", "market_as_of": as_of.strftime("%Y-%m-%d")}
    monkeypatch.setattr(service, "_load_phase1_dataset", lambda: (close, volume, eligibility, universe, metadata))

    frame, built_at = service.build_metric_frame()
    assert isinstance(built_at, datetime)
    assert "APCOTEXIND" in frame["Symbol"].tolist()
    row = frame.loc[frame["Symbol"] == "APCOTEXIND"].iloc[0]
    assert row["CMP"] > 0
    assert pd.notna(row["Momentum Score"])
    assert pd.notna(row["% EMA 200"])
    assert pd.notna(row["Volume Ratio"])

    monkeypatch.setattr(service.store, "get", lambda: frame.copy())
    monkeypatch.setattr(service.store, "built_at", built_at, raising=False)
    payload = ScreenerQuery.model_validate(
        {
            "filters": [{"field": "Symbol", "operator": "=", "value": "APCOTEXIND"}],
            "sort": {"field": "Rank", "direction": "asc"},
            "page": 1,
            "page_size": 10,
        }
    )
    result = service.query(payload)
    assert result["total"] == 1
    assert result["rows"][0]["Symbol"] == "APCOTEXIND"
