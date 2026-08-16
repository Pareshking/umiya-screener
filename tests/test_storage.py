import pytest

from src.storage import ObjectStoreConfig


def test_storage_config_requires_credentials(monkeypatch):
    for name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError):
        ObjectStoreConfig.from_env()


def test_storage_config_reads_environment(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://example.invalid")
    monkeypatch.setenv("S3_BUCKET", "umiya")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "public-example")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret-example")
    monkeypatch.setenv("S3_REGION", "auto")
    cfg = ObjectStoreConfig.from_env()
    assert cfg.bucket == "umiya"
    assert cfg.region == "auto"
