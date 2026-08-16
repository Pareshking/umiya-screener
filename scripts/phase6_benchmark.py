"""Phase 6 production performance benchmark.

This measures HTTP/API latency on the deployed Vercel/Render system without
changing production data or application behaviour. It is intentionally a
measurement tool, not a pass/fail smoke test.
"""
from __future__ import annotations

import csv
import os
import statistics
import time
from pathlib import Path

import httpx

API = os.getenv("PRODUCTION_API_URL", "https://umiya-screener-api.onrender.com").rstrip("/")
FRONTEND = os.getenv("PRODUCTION_FRONTEND_URL", "https://pareshpatel.vercel.app").rstrip("/")
RUNS = int(os.getenv("PHASE6_RUNS", "7"))
OUT = Path(os.getenv("PHASE6_OUTPUT", "phase6-benchmark.csv"))


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
    return ordered[index]


def measure(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[int, float, int]:
    start = time.perf_counter()
    response = client.request(method, url, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return response.status_code, elapsed, len(response.content)


def main() -> int:
    results: list[dict[str, object]] = []
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        health_code, _, _ = measure(client, "GET", f"{API}/api/v1/health")
        if health_code != 200:
            raise SystemExit(f"health check failed: HTTP {health_code}")

        metadata_code, _, _ = measure(client, "GET", f"{API}/api/v1/screener/metadata")
        if metadata_code != 200:
            raise SystemExit(f"metadata check failed: HTTP {metadata_code}")
        metadata = client.get(f"{API}/api/v1/screener/metadata").json()
        fields = metadata.get("fields", [])
        sort_field = "Rank" if any(f.get("name") == "Rank" for f in fields if isinstance(f, dict)) else "Symbol"

        base = {"filters": [], "sort": {"field": sort_field, "direction": "asc"}, "search": None, "page": 1, "page_size": 25}
        sample_symbol = None
        for _ in range(RUNS):
            code, ms, size = measure(client, "POST", f"{API}/api/v1/screener/query", json=base)
            if code != 200:
                raise SystemExit(f"query failed: HTTP {code}")
            if sample_symbol is None:
                rows = client.post(
                    f"{API}/api/v1/screener/query",
                    json={**base, "search": "APCOTEXIND"},
                ).json().get("rows", [])
                if rows:
                    sample_symbol = rows[0].get("Symbol")
                else:
                    rows = client.post(f"{API}/api/v1/screener/query", json=base).json().get("rows", [])
                    if rows:
                        sample_symbol = rows[0].get("Symbol")
            results.append({"operation": "screener_query", "run_ms": round(ms, 2), "status": code, "bytes": size})

        if not sample_symbol:
            raise SystemExit("could not select a production sample symbol")
        print(f"Injected-stock verification symbol: {sample_symbol}")

        operations = [
            ("numeric_filter", "POST", "/api/v1/screener/query", {**base, "filters": [{"field": "Momentum Score", "operator": ">", "value": 0}]}),
            ("multi_filter", "POST", "/api/v1/screener/query", {**base, "filters": [{"field": "Momentum Score", "operator": ">", "value": 0}, {"field": "12M Return", "operator": ">", "value": 0}]}),
            ("search", "POST", "/api/v1/screener/query", {**base, "search": sample_symbol}),
            ("sort", "POST", "/api/v1/screener/query", {**base, "sort": {"field": "Momentum Score", "direction": "desc"}}),
            ("export", "POST", "/api/v1/screener/export", base),
            ("stock_detail", "GET", f"/api/v1/stocks/{sample_symbol}", None),
            ("chart_3m", "GET", f"/api/v1/stocks/{sample_symbol}/chart?days=63", None),
            ("chart_6m", "GET", f"/api/v1/stocks/{sample_symbol}/chart?days=126", None),
            ("chart_1y", "GET", f"/api/v1/stocks/{sample_symbol}/chart?days=252", None),
            ("frontend", "GET", "/", None),
        ]

        for name, method, path, payload in operations:
            url = (FRONTEND if name == "frontend" else API) + path
            for _ in range(RUNS):
                code, ms, size = measure(client, method, url, json=payload) if payload is not None else measure(client, method, url)
                expected = 200
                if code != expected:
                    raise SystemExit(f"{name} failed: HTTP {code}")
                results.append({"operation": name, "run_ms": round(ms, 2), "status": code, "bytes": size})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["operation", "run_ms", "status", "bytes"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Phase 6 benchmark sample symbol: {sample_symbol}")
    print(f"Runs per operation: {RUNS}")
    print("Operation                 p50 ms    p95 ms    max ms")
    print("-" * 58)
    for operation in dict.fromkeys(str(r["operation"]) for r in results):
        values = [float(r["run_ms"]) for r in results if r["operation"] == operation]
        print(f"{operation:24} {statistics.median(values):8.0f} {percentile(values, .95):9.0f} {max(values):9.0f}")
    print(f"Saved raw measurements to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
