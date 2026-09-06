"""A published dataset must be able to reach a running container.

The outage this file exists for: _load_cache returned the local dataset
whenever it merely validated, without asking whether it was still fresh, and
only consulted R2 when the local copy was missing or corrupt. So a long-running
instance pinned itself to an ageing dataset -- past the TTL it raised "stale" on
every request and never looked at R2 again. The scheduled build published
successfully; the service stayed down anyway.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backend.app import service
from src.config import METRICS_CACHE_TTL_HOURS


def write_dataset(root, name, built_at, rows=3):
    ds = root / name
    ds.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "Symbol": [f"S{i}" for i in range(rows)],
        "Momentum Score": [float(i) for i in range(rows)],
        "Market As Of": [pd.Timestamp("2026-09-04")] * rows,
    }).to_parquet(ds / "screener_metrics.parquet", index=False)
    (ds / "metadata.json").write_text(json.dumps({
        "schema_version": "2.0", "built_at_utc": built_at.isoformat(),
        "rows": rows, "source_contract": ["adj_close", "volume"],
    }), encoding="utf-8")
    (root / "LATEST.json").write_text(json.dumps({"dataset": name}), encoding="utf-8")
    return ds


@pytest.fixture
def metrics_root(tmp_path, monkeypatch):
    root = tmp_path / "metrics"
    root.mkdir()
    monkeypatch.setattr(service, "METRICS_ROOT", root)
    monkeypatch.setattr(service, "METRICS_CACHE_PATH", tmp_path / "absent.parquet")
    return root


def test_a_stale_local_dataset_triggers_a_resync_instead_of_a_permanent_503(metrics_root, monkeypatch):
    """The actual outage, reproduced."""
    stale_at = datetime.now(timezone.utc) - timedelta(hours=METRICS_CACHE_TTL_HOURS + 10)
    write_dataset(metrics_root, "dataset_old", stale_at)

    fresh_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    synced = {"called": False}

    def fake_sync():
        # What the real sync does: pull the newer prefix and advance the pointer.
        synced["called"] = True
        write_dataset(metrics_root, "dataset_new", fresh_at)
        return True

    monkeypatch.setattr(service, "_sync_remote_metrics", fake_sync)

    result = service._load_cache()
    assert synced["called"], "a stale local dataset must prompt a re-sync"
    assert result is not None
    _, built_at = result
    assert built_at == fresh_at, "the newly published dataset must win"


def test_the_store_serves_the_resynced_dataset_rather_than_raising(metrics_root, monkeypatch):
    stale_at = datetime.now(timezone.utc) - timedelta(hours=METRICS_CACHE_TTL_HOURS + 10)
    write_dataset(metrics_root, "dataset_old", stale_at, rows=2)
    fresh_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    def fake_sync():
        write_dataset(metrics_root, "dataset_new", fresh_at, rows=7)
        return True

    monkeypatch.setattr(service, "_sync_remote_metrics", fake_sync)

    store = service.ScreenerStore()
    frame = store.get()            # must not raise MetricsCacheStale
    assert len(frame) == 7


def test_a_fresh_local_dataset_does_not_hit_the_network(metrics_root, monkeypatch):
    """The happy path must stay local; re-syncing on every read would be absurd."""
    write_dataset(metrics_root, "dataset_now", datetime.now(timezone.utc) - timedelta(minutes=1))

    def fail_sync():
        raise AssertionError("must not re-sync while the local dataset is fresh")

    monkeypatch.setattr(service, "_sync_remote_metrics", fail_sync)
    assert service._load_cache() is not None


def test_a_genuinely_dead_pipeline_still_reports_stale(metrics_root, monkeypatch):
    """Recovery must not become 'never notice'.

    If nothing newer exists anywhere, the store must still refuse the old data
    rather than quietly serving it.
    """
    stale_at = datetime.now(timezone.utc) - timedelta(hours=METRICS_CACHE_TTL_HOURS + 10)
    write_dataset(metrics_root, "dataset_old", stale_at)
    monkeypatch.setattr(service, "_sync_remote_metrics", lambda: False)

    store = service.ScreenerStore()
    with pytest.raises(service.MetricsCacheStale):
        store.get()


def test_a_missing_local_dataset_still_syncs(metrics_root, monkeypatch):
    fresh_at = datetime.now(timezone.utc) - timedelta(minutes=2)

    def fake_sync():
        write_dataset(metrics_root, "dataset_new", fresh_at)
        return True

    monkeypatch.setattr(service, "_sync_remote_metrics", fake_sync)
    result = service._load_cache()
    assert result is not None and result[1] == fresh_at
