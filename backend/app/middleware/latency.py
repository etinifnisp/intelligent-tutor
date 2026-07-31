"""Request latency tracking middleware."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("tutor.latency")

# Rolling window of recent request durations (ms)
_recent_latencies: Deque[float] = deque(maxlen=500)


def get_latency_stats() -> dict:
    if not _recent_latencies:
        return {"count": 0, "avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    values = sorted(_recent_latencies)
    n = len(values)
    p95_idx = min(n - 1, int(n * 0.95))
    return {
        "count": n,
        "avg_ms": round(sum(values) / n, 2),
        "p95_ms": round(values[p95_idx], 2),
        "max_ms": round(values[-1], 2),
    }


class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        _recent_latencies.append(elapsed_ms)
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        path = request.url.path
        if not path.startswith("/static"):
            logger.debug(
                "request_complete",
                extra={
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
        return response
