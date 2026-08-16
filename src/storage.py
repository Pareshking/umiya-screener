from __future__ import annotations

import json
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


def _client(store: ObjectStoreConfig):
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=store.endpoint_url,
        aws_access_key_id=store.access_key_id,
        aws_secret_access_key=store.secret_access_key,
        region_name=store.region,
    )


def upload_directory(store: ObjectStoreConfig, local_dir: Path, prefix: str) -> list[str]:
    client = _client(store)
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        key = f"{prefix.rstrip('/')}/{path.relative_to(local_dir).as_posix()}"
        client.put_object(Bucket=store.bucket, Key=key, Body=path.read_bytes())
        uploaded.append(key)
    return uploaded


def publish_pointer(store: ObjectStoreConfig, pointer_key: str, target: str) -> None:
    """Publish a pointer in the same JSON shape consumed by read_pointer."""
    body = json.dumps({"prefix": target.rstrip("/")}).encode("utf-8")
    _client(store).put_object(Bucket=store.bucket, Key=pointer_key, Body=body, ContentType="application/json")


def read_pointer(store: ObjectStoreConfig, pointer_key: str) -> str:
    body = _client(store).get_object(Bucket=store.bucket, Key=pointer_key)["Body"].read()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid object-store pointer: {pointer_key}") from exc
    prefix = payload.get("prefix")
    if not isinstance(prefix, str) or not prefix.strip():
        raise RuntimeError(f"Invalid object-store pointer: {pointer_key}")
    return prefix


def download_prefix(store: ObjectStoreConfig, prefix: str, destination: Path) -> int:
    """Download a complete prefix into a temporary destination.

    The caller should publish its local pointer only after this function returns
    successfully and validates the required files. A zero-object prefix is
    rejected so a remote outage cannot look like a valid empty dataset.
    """
    client = _client(store)
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    paginator = client.get_paginator("list_objects_v2")
    root = prefix.rstrip("/") + "/"
    for page in paginator.paginate(Bucket=store.bucket, Prefix=root):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            relative = key[len(root):]
            if not relative:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(client.get_object(Bucket=store.bucket, Key=key)["Body"].read())
            count += 1
    if count == 0:
        raise RuntimeError(f"Object-store prefix is empty: {prefix}")
    return count
