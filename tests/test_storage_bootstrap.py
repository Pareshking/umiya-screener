from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.storage import ObjectStoreConfig, read_pointer


def test_pointer_contract_uses_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    class Body:
        def read(self) -> bytes:
            return json.dumps({"prefix": "datasets/price_20260816"}).encode()

    class Client:
        def get_object(self, **kwargs):
            assert kwargs["Bucket"] == "test"
            assert kwargs["Key"] == "pointers/latest-price-dataset.json"
            return {"Body": Body()}

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    config = ObjectStoreConfig("https://example.invalid", "test", "key", "secret")
    assert read_pointer(config, "pointers/latest-price-dataset.json") == "datasets/price_20260816"


def test_pointer_contract_rejects_missing_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    class Body:
        def read(self) -> bytes:
            return b'{"dataset":"wrong-contract"}'

    class Client:
        def get_object(self, **kwargs):
            return {"Body": Body()}

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    config = ObjectStoreConfig("https://example.invalid", "test", "key", "secret")
    with pytest.raises(RuntimeError, match="Invalid object-store pointer"):
        read_pointer(config, "pointers/latest-price-dataset.json")


def test_fresh_bootstrap_downloads_remote_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from backend.app import main

    remote_dir = tmp_path / "remote"
    remote_dir.mkdir()
    (remote_dir / "metadata.json").write_text('{"market_as_of":"2026-08-15","data_contract":["adj_close","volume"]}')
    for name in ("adj_close.parquet", "volume.parquet", "eligibility.parquet", "universe.parquet"):
        (remote_dir / name).write_bytes(b"placeholder")

    monkeypatch.setattr(main, "PRICE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(main, "read_pointer", lambda remote, key: "datasets/price_20260816")

    def download(remote, prefix, destination):
        destination.mkdir(parents=True, exist_ok=True)
        for path in remote_dir.iterdir():
            (destination / path.name).write_bytes(path.read_bytes())
        return len(list(remote_dir.iterdir()))

    monkeypatch.setattr(main, "download_prefix", download)
    monkeypatch.setattr(main.ObjectStoreConfig, "from_env", classmethod(lambda cls: object()))

    dataset, metadata = main._ensure_price_dataset()
    assert dataset.name == "price_20260816"
    assert metadata["market_as_of"] == "2026-08-15"
    assert json.loads((tmp_path / "cache" / "LATEST.json").read_text())["dataset"] == "price_20260816"
