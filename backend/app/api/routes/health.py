from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.config import (
    CORPUS_PATH,
    DATABASE_PATH,
    FAISS_INDEX_PATH,
    FRONTEND_DIR,
    GRAPH_STORE_PATH,
    RETRIEVAL_MANIFEST_PATH,
)
from app.middleware.latency import get_latency_stats
from app.services.corpus import get_questions_ram

router = APIRouter()
logger = logging.getLogger("tutor.health")

_boot_time = time.time()


@router.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the React SPA index.html at the root URL."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return {"error": "Frontend not found. Run the app from the intelligent-tutor directory."}


@router.get("/health")
async def health():
    return {"status": "ok", "uptime_s": round(time.time() - _boot_time, 1)}


@router.get("/health/live")
async def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
async def health_ready(request: Request):
    checks: dict[str, object] = {}
    ok = True

    checks["database"] = DATABASE_PATH.exists()
    ok = ok and checks["database"]

    corpus_count = len(get_questions_ram())
    checks["corpus_loaded"] = corpus_count > 0
    checks["corpus_count"] = corpus_count
    ok = ok and checks["corpus_loaded"]

    checks["graph_store"] = GRAPH_STORE_PATH.exists()
    ok = ok and checks["graph_store"]

    retrieval = getattr(request.app.state, "retrieval", None)
    checks["retrieval_ready"] = bool(retrieval and getattr(retrieval, "ready", False))
    checks["retrieval_index"] = FAISS_INDEX_PATH.exists() and RETRIEVAL_MANIFEST_PATH.exists()
    ok = ok and checks["retrieval_ready"]

    checks["model_provider"] = os.getenv("MODEL_PROVIDER", "gemini")

    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ok else "degraded", "checks": checks},
    )


@router.get("/health/metrics")
async def health_metrics(request: Request):
    memory_mb = None
    try:
        import psutil

        memory_mb = round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except ImportError:
        pass

    retrieval = getattr(request.app.state, "retrieval", None)
    return {
        "uptime_s": round(time.time() - _boot_time, 1),
        "latency": get_latency_stats(),
        "memory_mb": memory_mb,
        "corpus_count": len(get_questions_ram()),
        "retrieval_ready": bool(retrieval and getattr(retrieval, "ready", False)),
        "model_provider": os.getenv("MODEL_PROVIDER", "gemini"),
    }
