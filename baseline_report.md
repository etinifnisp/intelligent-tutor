# Phase 1 Baseline Report

Generated: 2026-07-30T16:56:39.667734+00:00

## Purpose

Reproducible baseline snapshot of the Intelligent JEE Tutor prototype before
architecture changes (local models, SQLite, FAISS, verification pipeline).

## Corpus Freeze

- **Source:** `data\corpus\jee_corpus.json`
- **Frozen copy:** `data\corpus\frozen\jee_corpus_v1_baseline.json`
- **SHA-256:** `e73f66e9c04090d7d5d0386c92c2963f6d1650d6c5ba7ac2946cbbccf2820a9d`
- **Git tag:** `v0-baseline-prototype`
- **Questions:** 6,567

## Extraction Statistics

| Metric | Value |
|--------|-------|
| Total questions | 6,567 |
| Physics | 3,097 |
| Chemistry | 2,186 |
| Mathematics | 1,284 |
| MCQ-single | 6,487 |
| Integer | 80 |
| Year range | 2016–2025 |
| Unique papers | 149 |
| Unique chapters | 58 |
| Questions with answer text | 3,062 (46.6%) |
| Questions with options text | 4,207 (64.1%) |
| Diagram mentions | 649 |
| Integer-like (type or text) | 222 |

## Knowledge Graph (Canonical Topology)

| Metric | Value |
|--------|-------|
| Chapter nodes | 58 |
| Prerequisite edges | 37 |
| Hint-scaffold edges | 8 |
| Total canonical edges | 45 |

At runtime, question nodes are linked dynamically (≈6,567 question nodes).

## Gold Evaluation Set

- **Path:** `evaluation\gold_questions.jsonl`
- **Count:** 110 questions
- **Physics:** 39
- **Chemistry:** 45
- **Mathematics:** 26
- **MCQ:** 54
- **Diagram:** 24
- **Integer:** 32

## Response Latency (Baseline)

- **Method:** FastAPI TestClient (in-process, with startup)
- **Cold startup (corpus + graph load):** 1.74 s
- **Corpus loaded in RAM:** 6,567 questions

| Endpoint | Status | p50 (ms) | mean (ms) |
|----------|--------|----------|-----------|
| `/questions?limit=50` | 200 | 11.4 | 12.9 |
| `/chapters` | 200 | 3.3 | 3.4 |
| `/graph` | 200 | 460.4 | 485.6 |

## Technology Decisions (Phase 1)

See `hardware_profile.md` for full rationale.

| Decision | Selection |
|----------|-----------|
| Database | SQLite (hackathon default) |
| Vector search | FAISS |
| Keyword search | SQLite FTS5 (planned Phase 3) |
| Model runtime | Ollama |
| Embeddings | sentence-transformers (local) |

## Verification Checklist

- [x] Corpus frozen with SHA-256 manifest
- [x] Gold set ≥ 100 questions across subjects and types
- [x] Baseline metrics recorded
- [x] `.env.example` and `Makefile` setup command added
- [x] Git tag `v0-baseline-prototype` created (run `make tag-baseline`)

## Known Baseline Limitations

- Only ~47% of questions contain extractable answer text in `raw_text`.
- Difficulty labels are skewed (~89% marked Easy).
- Gemini API is still required for live tutoring in the prototype.
- Learner memory persists to JSON files (not transactional).
- Graph is chapter-level only (58 nodes, 43 canonical edges).
