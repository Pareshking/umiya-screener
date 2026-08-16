from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ObjectStoreConfig:
    endpoint_url: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    region: str = "auto"

    @classmethod
    def from_env(cls) -> "ObjectStoreConfig":
        values = {
            "endpoint_url": os.getenv("S3_ENDPOINT_URL", ""),
            "bucket": os.getenv("S3_BUCKET", ""),
            "access_key_id": os.getenv("S3_ACCESS_KEY_ID", ""),
            "secret_access_key": os.getenv("S3_SECRET_ACCESS_KEY", ""),
            "region": os.getenv("S3_REGION", "auto"),
        }
        missing = [key for key in ("endpoint_url", "bucket", "access_key_id", "secret_access_key") if not values[key]]
        if missing:
            raise RuntimeError("Missing object-storage configuration: " + ", ".join(missing))
        return cls(**values)


def upload_directory(store: ObjectStoreConfig, local_dir: Path, prefix: str) -> list[str]:
    """Upload an immutable local dataset directory to S3/R2.

    Existing keys are intentionally not overwritten. Publication of the active
    dataset is a separate pointer operation after all objects are uploaded and
    verified.
    """
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=store.endpoint_url,
        aws_access_key_id=store.access_key_id,
        aws_secret_access_key=store.secret_access_key,
        region_name=store.region,
    )
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        key = f"{prefix.rstrip('/')}/{path.relative_to(local_dir).as_posix()}"
        client.put_object(Bucket=store.bucket, Key=key, Body=path.read_bytes())
        uploaded.append(key)
    return uploaded


def publish_pointer(store: ObjectStoreConfig, pointer_key: str, target: str) -> None:
    """Publish the small active-version pointer only after candidate validation."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=store.endpoint_url,
        aws_access_key_id=store.access_key_id,
        aws_secret_access_key=store.secret_access_key,
        region_name=store.region,
    )
    client.put_object(Bucket=store.bucket, Key=pointer_key, Body=target.encode("utf-8"), ContentType="application/json")
