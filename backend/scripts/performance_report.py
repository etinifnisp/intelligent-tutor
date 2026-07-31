"""Local performance report — memory profile and API latency."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import EVAL_DIR  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    tracemalloc.start()
    t0 = time.perf_counter()
    app = create_app()
    boot_s = round(time.perf_counter() - t0, 2)

    endpoints = {
        "/health": "GET",
        "/health/ready": "GET",
        "/health/metrics": "GET",
        "/questions?limit=10": "GET",
        "/chapters": "GET",
    }
    latencies: dict[str, float] = {}
    with TestClient(app) as client:
        guest = client.post("/auth/guest").json()
        headers = {"Authorization": f"Bearer {guest['access_token']}"}
        for path, _method in endpoints.items():
            started = time.perf_counter()
            client.get(path, headers=headers if "/learning" in path else None)
            latencies[path] = round((time.perf_counter() - started) * 1000, 2)
        started = time.perf_counter()
        client.get("/learning/summary/me", headers=headers)
        latencies["/learning/summary/me"] = round(
            (time.perf_counter() - started) * 1000, 2
        )

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_mb = None
    try:
        import psutil

        memory_mb = round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except ImportError:
        pass

    report = {
        "boot_s": boot_s,
        "memory_mb": memory_mb,
        "tracemalloc_current_mb": round(current / (1024 * 1024), 2),
        "tracemalloc_peak_mb": round(peak / (1024 * 1024), 2),
        "endpoint_latency_ms": latencies,
        "checkpoint_pass": boot_s < 120 and all(v < 5000 for v in latencies.values()),
    }
    out = EVAL_DIR / "performance_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Boot: {boot_s}s | Peak mem: {report['tracemalloc_peak_mb']} MB")
    print(f"Report: {out}")
    return 0 if report["checkpoint_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
