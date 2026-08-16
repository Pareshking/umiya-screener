from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd


def _fixtures(symbols: list[str], periods: int = 130):
    index = pd.date_range("2025-01-01", periods=periods, freq="B")
    close = pd.DataFrame(index=index, columns=symbols, dtype=float)
    volume = pd.DataFrame(index=index, columns=symbols, dtype=float)
    for i, symbol in enumerate(symbols):
        close[symbol] = 100 + i * 5 + np.arange(periods) * 0.2
        volume[symbol] = 100_000 + i * 1_000
    universe = pd.DataFrame(
        {
            "Symbol": symbols,
            "Company Name": symbols,
            "Industry": ["Test"] * len(symbols),
            "Index": ["NIFTY_TEST"] * len(symbols),
        }
    )
    universe.attrs["warnings"] = []
    universe.attrs["duplicate_symbols"] = []
    universe.attrs["source_counts"] = {"NIFTY_TEST": len(symbols)}
    return close, volume, universe


def test_repeated_refreshes_publish_valid_datasets_and_advance_latest(monkeypatch, tmp_path):
    """Repeated successful refreshes must leave valid immutable datasets and one current pointer."""
    import scripts.build_data as build_data

    symbols = [f"TEST{i:03d}" for i in range(700)]
    close, volume, universe = _fixtures(symbols)

    monkeypatch.setattr(build_data, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(build_data, "load_universe", lambda: universe)
    monkeypatch.setattr(
        build_data,
        "fetch_prices",
        lambda requested: {"adj_close": close, "volume": volume},
    )

    first, first_meta = build_data.build()
    time.sleep(1.05)
    second, second_meta = build_data.build()

    assert first != second
    assert first.exists() and second.exists()
    assert first_meta["eligible_symbols"] == 700
    assert second_meta["eligible_symbols"] == 700
    latest = json.loads((tmp_path / "LATEST.json").read_text())
    assert latest["dataset"] == second.name
    assert not list(tmp_path.glob("*.tmp"))
    assert (first / "metadata.json").exists()
    assert (second / "metadata.json").exists()


def test_refresh_handles_membership_change_without_stale_symbols(monkeypatch, tmp_path):
    """A constituent replacement must update the next immutable dataset without mutating the prior one."""
    import scripts.build_data as build_data

    old_symbols = [f"TEST{i:03d}" for i in range(700)]
    new_symbols = old_symbols[:-1] + ["NEWSTOCK"]
    old_close, old_volume, old_universe = _fixtures(old_symbols)
    new_close, new_volume, new_universe = _fixtures(new_symbols)

    monkeypatch.setattr(build_data, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(build_data, "fetch_prices", lambda requested: {
        "adj_close": new_close if "NEWSTOCK" in requested else old_close,
        "volume": new_volume if "NEWSTOCK" in requested else old_volume,
    })

    current_universe = {"value": old_universe}
    monkeypatch.setattr(build_data, "load_universe", lambda: current_universe["value"])

    first, _ = build_data.build()
    current_universe["value"] = new_universe
    time.sleep(1.05)
    second, _ = build_data.build()

    first_saved = pd.read_parquet(first / "universe.parquet")
    second_saved = pd.read_parquet(second / "universe.parquet")
    assert "NEWSTOCK" not in first_saved["Symbol"].tolist()
    assert "TEST699" in first_saved["Symbol"].tolist()
    assert "NEWSTOCK" in second_saved["Symbol"].tolist()
    assert "TEST699" not in second_saved["Symbol"].tolist()
    assert first.exists() and second.exists()
    assert json.loads((tmp_path / "LATEST.json").read_text())["dataset"] == second.name
