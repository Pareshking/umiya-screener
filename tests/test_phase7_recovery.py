from pathlib import Path

import pytest

from src.storage import ObjectStoreConfig, download_prefix


def test_download_prefix_rejects_empty_remote(monkeypatch, tmp_path: Path):
    class Paginator:
        def paginate(self, **kwargs):
            return [{"Contents": []}]

    class Client:
        def get_paginator(self, name):
            assert name == "list_objects_v2"
            return Paginator()

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    config = ObjectStoreConfig("https://example.invalid", "test", "key", "secret")
    with pytest.raises(RuntimeError, match="Object-store prefix is empty"):
        download_prefix(config, "metrics/dataset_bad", tmp_path / "download")


def test_download_prefix_rejects_path_traversal(monkeypatch, tmp_path: Path):
    class Paginator:
        def paginate(self, **kwargs):
            return [{"Contents": [{"Key": "metrics/good/../escape.bin"}]}]

    class Client:
        def get_paginator(self, name):
            return Paginator()

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    config = ObjectStoreConfig("https://example.invalid", "test", "key", "secret")
    with pytest.raises(RuntimeError, match="Unsafe object-store path"):
        download_prefix(config, "metrics/good", tmp_path / "download")


def test_download_prefix_only_writes_objects_from_requested_prefix(monkeypatch, tmp_path: Path):
    class Body:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

    class Paginator:
        def paginate(self, **kwargs):
            return [{"Contents": [{"Key": "metrics/good/metadata.json"}, {"Key": "metrics/good/data.bin"}]}]

    class Client:
        def get_paginator(self, name):
            return Paginator()

        def get_object(self, **kwargs):
            values = {"metrics/good/metadata.json": b"{}", "metrics/good/data.bin": b"data"}
            return {"Body": Body(values[kwargs["Key"]])}

    monkeypatch.setattr("src.storage._client", lambda store: Client())
    config = ObjectStoreConfig("https://example.invalid", "test", "key", "secret")
    destination = tmp_path / "download"
    assert download_prefix(config, "metrics/good", destination) == 2
    assert (destination / "metadata.json").read_bytes() == b"{}"
    assert (destination / "data.bin").read_bytes() == b"data"
