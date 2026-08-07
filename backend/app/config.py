from pathlib import Path
import os

from dotenv import load_dotenv

# Load backend/.env before reading any secrets or model settings.
if not os.getenv("TESTING"):
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Project root: intelligent-tutor/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVAL_DIR = PROJECT_ROOT / "evaluation"
MIGRATIONS_DIR = PROJECT_ROOT / "backend" / "app" / "db" / "migrations"

CORPUS_PATH = DATA_DIR / "corpus" / "jee_corpus.json"
CORPUS_V2_PATH = DATA_DIR / "corpus" / "corpus_v2.jsonl"
CORPUS_VALIDATION_REPORT = DATA_DIR / "corpus" / "corpus_validation_report.md"
PAPERS_DIR = DATA_DIR / "papers"
IMAGES_DIR = DATA_DIR / "images"
GRAPH_STORE_PATH = DATA_DIR / "graph_store.json"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "app.db"))).resolve()
LEARNER_MEMORY_PATH = DATA_DIR / "learner_memory.json"  # legacy — migration only

INDEXES_DIR = DATA_DIR / "indexes"
RETRIEVAL_DB_PATH = INDEXES_DIR / "retrieval.db"
FAISS_INDEX_PATH = INDEXES_DIR / "faiss.index"
FAISS_IDS_PATH = INDEXES_DIR / "faiss_ids.json"
RETRIEVAL_MANIFEST_PATH = INDEXES_DIR / "manifest.json"
CONCEPT_NOTES_PATH = INDEXES_DIR / "concept_notes.jsonl"
RETRIEVAL_BENCHMARK_PATH = EVAL_DIR / "retrieval_benchmark.jsonl"
GOLD_QUESTIONS_PATH = EVAL_DIR / "gold_questions.jsonl"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
USE_LOCAL_RETRIEVAL = os.getenv("USE_LOCAL_RETRIEVAL", "true").lower() in {"1", "true", "yes"}
RETRIEVAL_CACHE_SIZE = max(1, int(os.getenv("RETRIEVAL_CACHE_SIZE", "256")))

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openrouter")  # openrouter | gemini | ollama | mock
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-3.5-flash-lite")
MODEL_FALLBACK_MODE = os.getenv("MODEL_FALLBACK_MODE", "mock")
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "30"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemini-3.5-flash-lite")


def get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY).strip()


def using_openrouter() -> bool:
    return bool(get_openrouter_api_key())
MAX_MESSAGE_LENGTH = max(256, int(os.getenv("MAX_MESSAGE_LENGTH", "4000")))
GUEST_RATE_LIMIT = max(1, int(os.getenv("GUEST_RATE_LIMIT", "20")))
GUEST_RATE_WINDOW_SECONDS = max(60.0, float(os.getenv("GUEST_RATE_WINDOW_SECONDS", "3600")))
APP_ENV = os.getenv("APP_ENV", "development").lower()
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000",
    ).split(",")
    if origin.strip()
)

LOG_FILE = PROJECT_ROOT / "backend" / "jee_tutor.log"

DEFAULT_JWT_SECRET = "dev-change-me-in-production"
JWT_SECRET = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "60"))
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))
