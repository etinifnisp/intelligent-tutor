from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
PAPERS_DIR = DATA_DIR / "papers"
IMAGES_DIR = DATA_DIR / "images"
EVAL_DIR = PROJECT_ROOT / "evaluation"

CORPUS_V1_PATH = CORPUS_DIR / "jee_corpus.json"
CORPUS_V2_PATH = CORPUS_DIR / "corpus_v2.jsonl"
VALIDATION_REPORT_PATH = CORPUS_DIR / "corpus_validation_report.md"
EXTRACTION_ERRORS_PATH = CORPUS_DIR / "extraction_errors.jsonl"
REVIEW_QUEUE_PATH = CORPUS_DIR / "review_queue.jsonl"
DIAGRAM_INDEX_PATH = CORPUS_DIR / "diagram_index.jsonl"
PAPER_REGISTRY_PATH = CORPUS_DIR / "paper_registry.json"
GOLD_QUESTIONS_PATH = EVAL_DIR / "gold_questions.jsonl"

SCHEMA_VERSION = "2.0"
PIPELINE_VERSION = "2.0.0"
