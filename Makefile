# Intelligent JEE Tutor — Phase 1 setup and baseline commands
# Windows: use `make` from Git Bash, or run equivalent commands manually.

PYTHON ?= python
VENV_DIR := backend/venv
VENV_BIN := $(VENV_DIR)/Scripts
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

.PHONY: help setup setup-backend setup-frontend baseline tag-baseline run-backend run-frontend verify corpus-v2 validate-corpus migrate-db build-retrieval-index eval-retrieval test-orchestrator test-verification eval-verification test-learning test test-integration test-e2e eval-all perf-report backup-db load-test

help:
	@echo "Intelligent JEE Tutor — available targets:"
	@echo "  make setup          Install backend + frontend dependencies"
	@echo "  make baseline       Freeze corpus, build gold set, write baseline report"
	@echo "  make tag-baseline   Create git tag v0-baseline-prototype"
	@echo "  make verify         Run baseline + import-check"
	@echo "  make run-backend    Start FastAPI (cd backend; python app.py)"
	@echo "  make corpus-v2      Build trustworthy corpus_v2.jsonl (Phase 2)"
	@echo "  make migrate-db       Run DB migrations + legacy JSON import"
	@echo "  make build-retrieval-index  Build FTS5 + FAISS indexes (Phase 4)"
	@echo "  make eval-retrieval   Run retrieval Recall@5 benchmark"
	@echo "  make test-orchestrator  Run Phase 5 orchestrator tests (mock model)"
	@echo "  make test-verification  Run Phase 6 verification tests"
	@echo "  make eval-verification  Run gold-set verification benchmark"
	@echo "  make test-learning      Run Phase 7 BKT/mastery tests"
	@echo "  make test               Run full pytest suite"
	@echo "  make test-integration   Run API integration tests"
	@echo "  make eval-all           Run all offline evaluations"
	@echo "  make eval-corpus        Run corpus quality evaluation"
	@echo "  make eval-tutor         Run tutor gold-set evaluation"
	@echo "  make perf-report        Generate performance report"
	@echo "  make backup-db          Backup SQLite database"
	@echo "  make load-test          Run Locust load test (headless)"
	@echo "  make test-e2e           Run Playwright end-to-end tests"

# Single setup command (Phase 1 deliverable)
setup: setup-backend setup-frontend
	@echo ""
	@echo "Setup complete."
	@echo "  1. Copy .env.example to backend/.env and set GOOGLE_API_KEY"
	@echo "  2. Run: make baseline"
	@echo "  3. Run: make run-backend  (terminal 1)"
	@echo "  4. Run: make run-frontend (terminal 2)"

setup-backend:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r backend/requirements.txt

setup-frontend:
	cd frontend ; npm install

baseline:
	$(PYTHON) backend/scripts/collect_baseline.py

tag-baseline:
	git tag -a v0-baseline-prototype -m "Phase 1 baseline: frozen corpus and prototype snapshot"

verify: baseline
	$(PYTHON) -c "import sys; sys.path.insert(0,'backend'); from app.main import create_app; create_app(); print('App factory OK')"

corpus-v2:
	$(PYTHON) -m pipelines.build_corpus_v2

validate-corpus: corpus-v2
	$(PYTHON) -m pipelines.validate_corpus

migrate-db:
	$(PYTHON) -c "import sys; sys.path.insert(0,'backend'); from app.db import init_database; init_database(); print('DB ready')"
	$(PYTHON) backend/scripts/migrate_learner_json.py

build-retrieval-index:
	$(PYTHON) -m pipelines.build_retrieval_index

eval-retrieval: build-retrieval-index
	$(PYTHON) evaluation/retrieval_eval.py

test-orchestrator:
	cd backend ; $(PYTHON) -m pytest tests/test_orchestrator.py -q

test-verification:
	cd backend ; $(PYTHON) -m pytest tests/test_verification.py -q

eval-verification:
	$(PYTHON) evaluation/verification_eval.py

test-learning:
	cd backend ; $(PYTHON) -m pytest tests/test_learning.py -q

test:
	cd backend ; $(PYTHON) -m pytest -q

test-integration:
	cd backend ; $(PYTHON) -m pytest tests/test_api_integration.py tests/test_conversation_store.py -q

eval-corpus:
	$(PYTHON) -m evaluation.corpus_eval

eval-tutor:
	$(PYTHON) -m evaluation.tutor_eval

eval-all: build-retrieval-index
	$(PYTHON) -m evaluation.run_all

perf-report:
	cd backend ; $(PYTHON) scripts/performance_report.py

backup-db:
	cd backend ; $(PYTHON) scripts/backup_db.py backup

load-test:
	locust -f locust/locustfile.py --host http://127.0.0.1:8000 --headless -u 10 -r 2 -t 30s

test-e2e:
	cd e2e ; npm install ; npx playwright install chromium ; npm test

run-backend:
	cd backend ; $(PYTHON) app.py

run-frontend:
	cd frontend ; npm run dev
