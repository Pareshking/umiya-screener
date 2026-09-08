"""The chart pane must follow the price pointer, not the startup download.

On 2026-09-08 the screener was corrected to Tuesday's settled close while the
chart pane went on drawing the midday bar -- RELIANCE at 4.0M shares against
the real 9.8M -- because the two read different datasets and only the metrics
one followed its pointer. _ensure_price_dataset returns the local copy the
moment it validates and consults R2 only when it is missing or corrupt, so a
running container charted whatever it downloaded at startup, indefinitely.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from backend.app import main


def write_price_dataset(root, name, last_date, volume):
    ds = root / name
    ds.mkdir(parents=True, exist_ok=True)
    index = pd.bdate_range(end=last_date, periods=3)
    pd.DataFrame({"RELIANCE": [1.0, 2.0, 3.0]}, index=index).to_parquet(ds / "adj_close.parquet")
    pd.DataFrame({"RELIANCE": [1, 2, volume]}, index=index).to_parquet(ds / "volume.parquet")
    pd.DataFrame({"Symbol": ["RELIANCE"], "History Days": [3]}).to_parquet(ds / "eligibility.parquet", index=False)
    pd.DataFrame({"Symbol": ["RELIANCE"], "Index": ["NIFTY 750"]}).to_parquet(ds / "universe.parquet", index=False)
    (ds / "metadata.json").write_text(json.dumps({
        "schema_version": "1.2", "data_contract": ["adj_close", "volume"],
        "market_as_of": str(pd.Timestamp(last_date).date()),
    }), encoding="utf-8")
    return ds


def set_pointer(root, name):
    (root / "LATEST.json").write_text(json.dumps({"dataset": name}), encoding="utf-8")


@pytest.fixture
def price_root(tmp_path, monkeypatch):
    root = tmp_path / "price_history"
    root.mkdir()
    monkeypatch.setattr(main, "PRICE_ROOT", root)
    return root


@pytest.fixture
def fake_remote(monkeypatch):
    state = {"dataset": None, "downloads": 0}

    monkeypatch.setattr(main.ObjectStoreConfig, "from_env", staticmethod(lambda: object()))
    monkeypatch.setattr(main, "read_pointer", lambda store, key: f"datasets/{state['dataset']}")

    def fake_download(store, prefix, destination):
        state["downloads"] += 1
        write_price_dataset(destination.parent, destination.name, state["last_date"], state["volume"])

    monkeypatch.setattr(main, "download_prefix", fake_download)
    return state


def test_the_chart_dataset_follows_a_newer_pointer(price_root, fake_remote):
    """The bug: a valid local copy pinned the charts forever."""
    write_price_dataset(price_root, "dataset_midday", "2026-09-08", volume=4_048_044)
    set_pointer(price_root, "dataset_midday")

    fake_remote.update(dataset="dataset_settled", last_date="2026-09-08", volume=9_797_263)
    assert main.adopt_newer_price_dataset() is True

    name = json.loads((price_root / "LATEST.json").read_text())["dataset"]
    assert name == "dataset_settled"
    volume = pd.read_parquet(price_root / name / "volume.parquet")["RELIANCE"].iloc[-1]
    assert volume == 9_797_263, "the chart would still draw the partial session"


def test_an_unchanged_pointer_downloads_nothing(price_root, fake_remote):
    write_price_dataset(price_root, "dataset_a", "2026-09-08", volume=100)
    set_pointer(price_root, "dataset_a")
    fake_remote.update(dataset="dataset_a", last_date="2026-09-08", volume=100)

    assert main.adopt_newer_price_dataset() is False
    assert fake_remote["downloads"] == 0, "37MB must not be re-downloaded every poll"


def test_a_superseded_dataset_is_deleted(price_root, fake_remote):
    """Adopting daily without pruning fills a small ephemeral disk."""
    write_price_dataset(price_root, "dataset_old", "2026-09-07", volume=1)
    set_pointer(price_root, "dataset_old")
    fake_remote.update(dataset="dataset_new", last_date="2026-09-08", volume=2)

    assert main.adopt_newer_price_dataset() is True
    remaining = sorted(p.name for p in price_root.glob("dataset_*"))
    assert remaining == ["dataset_new"], f"stale datasets left on disk: {remaining}"


def test_a_failed_download_leaves_the_current_dataset_serving(price_root, fake_remote, monkeypatch):
    write_price_dataset(price_root, "dataset_good", "2026-09-08", volume=500)
    set_pointer(price_root, "dataset_good")
    fake_remote.update(dataset="dataset_broken", last_date="2026-09-08", volume=1)

    def boom(*args, **kwargs):
        raise RuntimeError("R2 unreachable")

    monkeypatch.setattr(main, "download_prefix", boom)

    assert main.adopt_newer_price_dataset() is False
    assert json.loads((price_root / "LATEST.json").read_text())["dataset"] == "dataset_good"
    assert (price_root / "dataset_good").exists()


def test_an_unreachable_pointer_is_not_fatal(price_root, monkeypatch):
    write_price_dataset(price_root, "dataset_good", "2026-09-08", volume=500)
    set_pointer(price_root, "dataset_good")

    def boom(*args, **kwargs):
        raise RuntimeError("no credentials")

    monkeypatch.setattr(main, "read_pointer", boom)
    assert main.adopt_newer_price_dataset() is False


def test_the_poller_updates_both_datasets_independently(monkeypatch):
    """A failure on one must not stop the other; half a site updating is
    harder to notice than none of it."""
    import threading

    seen = {"price": threading.Event()}

    def failing_metrics():
        raise RuntimeError("metrics sync down")

    monkeypatch.setattr(main, "DATASET_POLL_SECONDS", 0.01)
    monkeypatch.setattr(main.store, "adopt_newer_published_dataset", failing_metrics)
    monkeypatch.setattr(main, "adopt_newer_price_dataset", lambda: (seen["price"].set(), False)[1])

    main.poll_for_newer_dataset()
    assert seen["price"].wait(timeout=5), "a metrics failure suppressed the price update"
