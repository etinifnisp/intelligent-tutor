import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, graph_routes, health, learning, memory, questions, retrieval, tutor
from app.config import (
    APP_ENV,
    CORS_ORIGINS,
    DEFAULT_JWT_SECRET,
    FRONTEND_DIR,
    GRAPH_STORE_PATH,
    IMAGES_DIR,
    JWT_SECRET,
    MODEL_PROVIDER,
    USE_LOCAL_RETRIEVAL,
)
from app.db import init_database
from app.logging_config import setup_logging
from app.middleware.latency import LatencyMiddleware
from app.services.auth_service import ensure_admin_user, ensure_demo_user
from app.services.conversation_store import ConversationStore
from app.services.corpus import get_questions_ram, load_questions_into_ram
from app.services.gemini_sync import synchronize_file_search_store
from app.services.knowledge_graph import KnowledgeGraphManager
from app.services.learner_store import LearnerStore
from app.retrieval.service import RetrievalService
from app.tutor.model_gateway import create_model_gateway
from app.tutor.orchestrator import TutorOrchestrator
from app.learning.mastery_service import MasteryService
from app.verification.service import VerificationService

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
setup_logging()
logger_boot = logging.getLogger("tutor.boot")
logger_graph = logging.getLogger("tutor.graph")


def create_app() -> FastAPI:
    app = FastAPI(title="JEE Intelligent Tutor Backend Engine")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(CORS_ORIGINS),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LatencyMiddleware)

    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
        logging.getLogger("tutor.server").info("Frontend static files mounted from: %s", FRONTEND_DIR)
    else:
        logging.getLogger("tutor.server").warning(
            "Frontend directory not found at %s — static files will not be served.",
            FRONTEND_DIR,
        )

    if IMAGES_DIR.exists():
        app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
        logging.getLogger("tutor.server").info("Images mounted from: %s", IMAGES_DIR)
    else:
        logging.getLogger("tutor.server").warning("Images directory not found at %s", IMAGES_DIR)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(questions.router)
    app.include_router(graph_routes.router)
    app.include_router(memory.router)
    app.include_router(learning.router)
    app.include_router(retrieval.router)
    app.include_router(tutor.router)

    @app.on_event("startup")
    async def boot_sequence():
        if APP_ENV in {"production", "prod"} and JWT_SECRET == DEFAULT_JWT_SECRET:
            raise RuntimeError("JWT_SECRET must be configured for production.")
        if APP_ENV in {"production", "prod"} and os.getenv("ADMIN_PASSWORD", "admin123") == "admin123":
            raise RuntimeError("ADMIN_PASSWORD must be configured for production.")
        logger_boot.info("=" * 60)
        logger_boot.info("JEE Intelligent Tutor — Boot Sequence Starting")
        logger_boot.info("    Timestamp : %s", datetime.now().isoformat())
        logger_boot.info("=" * 60)

        init_database()
        ensure_admin_user()
        ensure_demo_user()
        app.state.learner_store = LearnerStore()
        app.state.conversation_store = ConversationStore()

        load_questions_into_ram()
        if not USE_LOCAL_RETRIEVAL:
            asyncio.create_task(synchronize_file_search_store(app))
        else:
            logger_boot.info("Local retrieval enabled — skipping Gemini File Search sync.")

        app.state.retrieval = RetrievalService()
        if not app.state.retrieval.load():
            logger_boot.warning("Retrieval service not loaded — run build_retrieval_index.")

        app.state.orchestrator = TutorOrchestrator(model_gateway=create_model_gateway(MODEL_PROVIDER))
        app.state.verification = VerificationService()
        app.state.mastery = MasteryService(app.state.learner_store)
        logger_boot.info("Tutor orchestrator ready (model_provider=%s).", MODEL_PROVIDER)

        logger_graph.info("Initialising Knowledge Graph Manager...")
        app.state.graph = KnowledgeGraphManager(
            storage_path=str(GRAPH_STORE_PATH),
            learner_store=app.state.learner_store,
        )
        questions_ram = get_questions_ram()
        if questions_ram:
            logger_graph.info("Linking %s questions to graph nodes...", f"{len(questions_ram):,}")
            app.state.graph.link_questions(questions_ram)

        logger_boot.info("=" * 60)
        logger_boot.info("Boot sequence complete — ready for connections.")
        logger_boot.info("=" * 60)

    return app


app = create_app()
