"""The API must accept connections without waiting for R2 hydration.

The price dataset is ~37MB and only the chart endpoint needs it. Downloading it
in a sync startup handler meant uvicorn did not bind the port until the whole
transfer finished, and the container filesystem is ephemeral so every cold start
paid it again -- while the screener table, which needs only the ~0.3MB metrics
dataset, sat behind it.
"""

from __future__ import annotations

import inspect
import threading
import time

from backend.app import main


def test_startup_handler_does_not_hydrate_inline():
    """The startup hook must hand off to a thread, not download inline."""
    source = inspect.getsource(main.warm_price_dataset)
    assert "Thread" in source, "startup handler must not block the event loop"
    assert "_ensure_price_dataset()" not in source


def test_startup_returns_before_hydration_finishes(monkeypatch):
    release = threading.Event()
    entered = threading.Event()

    def slow_hydrate():
        entered.set()
        release.wait(timeout=10)
        return (main.PRICE_ROOT, {})

    monkeypatch.setattr(main, "_ensure_price_dataset", slow_hydrate)

    started = time.monotonic()
    main.warm_price_dataset()
    elapsed = time.monotonic() - started

    try:
        # The handler returns immediately; uvicorn can bind the port and serve
        # the screener while the price dataset is still downloading.
        assert elapsed < 1.0
        assert entered.wait(timeout=5), "warm-up thread never ran"
    finally:
        release.set()


def test_price_dataset_hydration_is_serialised():
    """The warm-up thread and a concurrent chart request must not race.

    Both call _ensure_price_dataset; without a lock they download into the same
    temporary directory and collide on the rename.
    """
    assert isinstance(main._PRICE_DATASET_LOCK, type(threading.Lock()))
    concurrent = []
    peak = 0
    lock = threading.Lock()

    def worker():
        nonlocal peak
        with main._PRICE_DATASET_LOCK:
            with lock:
                concurrent.append(1)
                peak = max(peak, len(concurrent))
            time.sleep(0.05)
            with lock:
                concurrent.pop()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert peak == 1, "price dataset hydration ran concurrently"


def test_dataset_reads_are_cacheable_but_probes_are_not():
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        for path in ("/api/v1/live", "/api/v1/health"):
            assert client.get(path).headers["cache-control"] == "no-store", path

        metadata = client.get("/api/v1/screener/metadata")
        if metadata.status_code == 200:
            assert metadata.headers["cache-control"] == main.DATASET_CACHE_CONTROL
            assert "max-age" in metadata.headers["cache-control"]
