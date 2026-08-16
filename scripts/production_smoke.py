"""Small production smoke test for the public API.

Usage:
  python scripts/production_smoke.py https://your-api.example.com
"""
from __future__ import annotations

import sys
import time

import httpx


def main(base: str) -> int:
    base = base.rstrip("/")
    checks = [
        ("health", "GET", "/api/v1/health", None),
        ("metadata", "GET", "/api/v1/screener/metadata", None),
        (
            "query",
            "POST",
            "/api/v1/screener/query",
            {"filters": [], "sort": {"field": "Rank", "direction": "asc"}, "search": None, "page": 1, "page_size": 5},
        ),
    ]
    failures = 0
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for name, method, path, payload in checks:
            start = time.perf_counter()
            try:
                response = client.request(method, base + path, json=payload)
                elapsed = (time.perf_counter() - start) * 1000
                print(f"{name}: HTTP {response.status_code} ({elapsed:.0f} ms)")
                if response.status_code >= 400:
                    failures += 1
            except Exception as exc:
                print(f"{name}: ERROR {exc}")
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/production_smoke.py https://api.example.com")
    raise SystemExit(main(sys.argv[1]))
