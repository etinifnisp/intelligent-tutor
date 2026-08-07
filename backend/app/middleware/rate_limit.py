"""Simple in-memory rate limiting for auth and abuse-prone endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import DefaultDict

_lock = Lock()
_hits: DefaultDict[str, list[float]] = defaultdict(list)


def allow_request(key: str, *, limit: int, window_seconds: float) -> bool:
    now = time.monotonic()
    with _lock:
        recent = [ts for ts in _hits[key] if now - ts < window_seconds]
        if len(recent) >= limit:
            _hits[key] = recent
            return False
        recent.append(now)
        _hits[key] = recent
        return True
