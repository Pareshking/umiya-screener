"""Publish a validated local dataset version to S3-compatible R2.

Credentials are read only from environment variables. The command uploads the
immutable version first and advances the pointer only after all files upload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage import ObjectStoreConfig, publish_pointer, upload_directory  # noqa: E402


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Local dataset directory")
    parser.add_argument("--prefix", required=True, help="Immutable object prefix")
    parser.add_argument("--pointer", required=True, help="Pointer key, e.g. pointers/latest-metrics.json")
    args = parser.parse_args()

    local_dir = Path(args.dataset).resolve()
    if not local_dir.is_dir():
        raise SystemExit(f"Dataset directory does not exist: {local_dir}")

    store = ObjectStoreConfig.from_env()
    keys = upload_directory(store, local_dir, args.prefix)
    if not keys:
        raise SystemExit("Dataset directory contains no files")

    target = json.dumps({"prefix": args.prefix.rstrip("/")}, separators=(",", ":"))
    publish_pointer(store, args.pointer, target)
    print(json.dumps({"uploaded_objects": len(keys), "pointer": args.pointer, "target": args.prefix}, indent=2))
