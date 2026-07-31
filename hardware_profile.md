# Hardware Profile and Local Stack Decisions

Phase 1 baseline — frozen before architecture migration.

## Target Deployment Hardware

### Minimum (demo / development)

| Component | Specification |
|-----------|---------------|
| CPU | 4 cores (Intel i5 / Ryzen 5 or equivalent) |
| RAM | 16 GB |
| GPU | Optional (CPU-only inference works with small models) |
| Storage | 20 GB free (corpus, indexes, models, papers) |
| OS | Windows 10/11, Ubuntu 22.04+, or macOS 13+ |

### Recommended (smooth local tutoring)

| Component | Specification |
|-----------|---------------|
| CPU | 8+ cores |
| RAM | 32 GB |
| GPU | NVIDIA 8 GB+ VRAM (for 7B–8B quantized models) |
| Storage | 50 GB SSD |
| OS | Ubuntu 22.04 LTS or Windows 11 with WSL2 |

### Model sizing by hardware

| Profile | Tutor model | Embedding model | Notes |
|---------|-------------|-----------------|-------|
| Low memory | `llama3.2:3b` or `phi3:mini` via Ollama | `all-MiniLM-L6-v2` | Intent + hints only; longer derivations may be weak |
| Balanced | `llama3.1:8b` Q4 via Ollama | `all-MiniLM-L6-v2` | Good hackathon default |
| High | `qwen2.5:14b` Q4 or `llama3.1:70b` Q4 | `bge-small-en-v1.5` | Better multi-step reasoning |

---

## Technology Selections (Phase 1)

### Database: SQLite

**Selected:** SQLite with WAL mode.

**Rationale:**

- Zero external services — runs fully local.
- Single-file database simplifies hackathon setup and backup.
- Sufficient for one FastAPI worker and demo-scale concurrent users.
- Direct migration path to PostgreSQL later (same SQLAlchemy models).

**Use PostgreSQL instead when:**

- Running multiple FastAPI workers.
- Load-testing with many simultaneous students.
- Team wants Docker Compose parity with production.

### Vector search: FAISS

**Selected:** FAISS (CPU index, `IndexFlatIP` or `IndexHNSW`).

**Rationale:**

- No database extension required.
- Fast to build and load from disk (`data/indexes/`).
- Works offline with sentence-transformers embeddings.
- pgvector adds Docker dependency without benefit at hackathon scale.

**Use pgvector instead when:**

- Already on PostgreSQL.
- Need transactional consistency between vectors and relational data.
- Deploying multi-worker retrieval service.

### Model runtime: Ollama

**Selected:** Ollama as the default local model gateway.

**Rationale:**

- One-command model pull (`ollama pull llama3.2:3b`).
- OpenAI-compatible HTTP API for easy adapter swapping.
- Supports quantized models on consumer hardware.
- llama.cpp remains a fallback for embedded or CI mock runs.

### Keyword search: SQLite FTS5 (planned Phase 3)

Prototype currently filters in-memory. Phase 3 will add FTS5 tables alongside FAISS hybrid retrieval.

### Embeddings: sentence-transformers

**Default:** `sentence-transformers/all-MiniLM-L6-v2` (~80 MB, CPU-friendly).

---

## Expected Resource Usage (Baseline Prototype)

| Operation | RAM | Latency (typical) |
|-----------|-----|-------------------|
| Backend startup (corpus + graph) | ~200–400 MB | 2–8 s |
| `/questions` API (50 items) | — | < 50 ms |
| `/graph` API | — | < 100 ms |
| Ollama 3B inference (hint) | +2–4 GB | 1–3 s |
| FAISS search (6k vectors) | +100 MB | < 10 ms |

---

## Network Requirements

| Mode | Internet needed? |
|------|------------------|
| Current prototype (Gemini) | Yes — `GOOGLE_API_KEY` |
| Target local stack (Phase 4+) | No — after models are pulled |
| Corpus rebuild | No — papers stored locally |

---

## Files and Paths

```text
intelligent-tutor/
├── data/
│   ├── corpus/frozen/     # Immutable Phase 1 snapshot
│   ├── indexes/           # FAISS + FTS (Phase 3+)
│   └── app.db             # SQLite (Phase 5+)
├── evaluation/
│   └── gold_questions.jsonl
├── .env.example
└── Makefile
```
