"""Production smoke test for the public Umiya Screener API and frontend."""
from __future__ import annotations

import csv
import io
import os
import statistics
import time

import httpx

API = os.getenv("PRODUCTION_API_URL", "https://umiya-screener-api.onrender.com").rstrip("/")
FRONTEND = os.getenv("PRODUCTION_FRONTEND_URL", "https://pareshpatel.vercel.app").rstrip("/")


def main() -> int:
    failures = 0
    timings: list[float] = []
    payload_sizes: dict[str, int] = {}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        def check(name: str, method: str, path: str, payload=None, expected=200):
            nonlocal failures
            start = time.perf_counter()
            try:
                r = client.request(method, API + path, json=payload)
                elapsed = (time.perf_counter() - start) * 1000
                print(f"{name}: HTTP {r.status_code} ({elapsed:.0f} ms, {len(r.content)} bytes)")
                payload_sizes[name] = len(r.content)
                if r.status_code != expected:
                    print(r.text[:500])
                    failures += 1
                return r, elapsed
            except Exception as exc:
                print(f"{name}: ERROR {exc}")
                failures += 1
                return None, 0.0

        # Render can cold-start the service. Hit readiness first so the
        # wake-up request is allowed to complete before the cheap liveness
        # assertion. This avoids a false-negative caused solely by request
        # ordering while still checking both endpoints independently.
        r, _ = check("readiness", "GET", "/api/v1/ready")
        if r:
            data = r.json()
            if data.get("status") != "ready" or data.get("dataset_ready") is not True:
                failures += 1

        r, _ = check("liveness", "GET", "/api/v1/live")
        if r:
            if r.json().get("status") != "alive" or not r.headers.get("x-request-id"):
                failures += 1

        r, _ = check("health", "GET", "/api/v1/health")
        if r:
            data = r.json()
            if data.get("status") != "ok" or data.get("dataset_ready") is not True:
                print("health payload is not production-ready")
                failures += 1

        r, _ = check("metadata", "GET", "/api/v1/screener/metadata")
        if not r:
            return 1
        metadata = r.json()
        universe_size = int(metadata.get("universe", 0))
        if universe_size < 600:
            print(f"implausibly small universe={universe_size}")
            failures += 1

        payload = {"filters": [], "sort": {"field": "Rank", "direction": "asc"}, "search": None, "page": 1, "page_size": 10}
        sample_symbol = None
        for i in range(5):
            r, elapsed = check(f"query-{i+1}", "POST", "/api/v1/screener/query", payload)
            timings.append(elapsed)
            if r:
                rows = r.json().get("rows", [])
                if not rows or r.json().get("total", 0) <= 0:
                    failures += 1
                elif sample_symbol is None:
                    sample_symbol = rows[0].get("Symbol")

        if not sample_symbol:
            print("Unable to select a live sample symbol from the screener")
            failures += 1
        else:
            search = {"filters": [], "sort": {"field": "Momentum Score", "direction": "desc"}, "search": sample_symbol, "page": 1, "page_size": 10}
            r, _ = check("search-sort", "POST", "/api/v1/screener/query", search)
            if r and not any(row.get("Symbol") == sample_symbol for row in r.json().get("rows", [])):
                failures += 1

            r, _ = check("stock-detail", "GET", f"/api/v1/stocks/{sample_symbol}")
            if r and r.json().get("Symbol") != sample_symbol:
                failures += 1

            for days in (63, 126, 252):
                r, _ = check(f"chart-{days}d", "GET", f"/api/v1/stocks/{sample_symbol}/chart?days={days}")
                if r and not r.json().get("rows"):
                    failures += 1

        r, _ = check("export", "POST", "/api/v1/screener/export", payload)
        if r:
            if "text/csv" not in r.headers.get("content-type", "") or "attachment" not in r.headers.get("content-disposition", "").lower():
                failures += 1
            try:
                rows = list(csv.reader(io.StringIO(r.text)))
                if len(rows) < 2 or "Symbol" not in rows[0]:
                    failures += 1
            except Exception:
                failures += 1

        check("missing-stock-404", "GET", "/api/v1/stocks/NOT_A_REAL_SYMBOL", expected=404)
        check("bad-filter-400", "POST", "/api/v1/screener/query", {"filters": [{"field": "NO_SUCH_FIELD", "operator": ">", "value": 1}]}, expected=400)
        check("bad-sort-400", "POST", "/api/v1/screener/query", {"filters": [], "sort": {"field": "NO_SUCH_SORT", "direction": "asc"}, "page": 1, "page_size": 10}, expected=400)

        try:
            r = client.get(API + "/api/v1/health", headers={"Origin": FRONTEND})
            allow = r.headers.get("access-control-allow-origin")
            print(f"cors: {allow}")
            if allow != FRONTEND:
                failures += 1
        except Exception as exc:
            print(f"cors: ERROR {exc}")
            failures += 1

        try:
            r = client.get(FRONTEND + "/")
            print(f"frontend: HTTP {r.status_code} ({len(r.content)} bytes)")
            if r.status_code != 200:
                failures += 1
        except Exception as exc:
            print(f"frontend: ERROR {exc}")
            failures += 1

    if timings:
        print(f"query latency: p50={statistics.median(timings):.0f} ms p95={sorted(timings)[max(0, int(len(timings)*.95)-1)]:.0f} ms")
    if payload_sizes:
        print("payload sizes: " + ", ".join(f"{name}={size}B" for name, size in payload_sizes.items()))
    print("PRODUCTION SMOKE: PASS" if failures == 0 else f"PRODUCTION SMOKE: FAIL ({failures} checks)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
