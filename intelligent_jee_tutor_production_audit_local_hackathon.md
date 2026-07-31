# Intelligent JEE Tutor — Production Audit and Zero-Cost Local Implementation Plan

## 1. Objective

This document audits the current `intelligent-tutor/` project and defines a practical implementation plan for turning it into a reliable JEE tutoring product suitable for a hackathon demonstration.

The revised system must:

- Run fully on a local machine.
- Require no paid cloud services.
- Avoid Firebase, Auth0, hosted vector databases, hosted object storage, and paid model APIs.
- Continue to use the existing JEE corpus and research pipeline.
- Provide verified explanations instead of unrestricted chatbot responses.
- Track actual learner performance rather than conversational sentiment.
- Support adaptive practice, hints, misconception detection, and revision planning.
- Remain simple enough to build during a hackathon.
- Provide a clear upgrade path for later production deployment.

The target product is not merely an AI chat interface. It should function as:

> A locally deployed, evidence-based JEE tutor that retrieves verified questions, guides students with progressive hints, checks solutions using deterministic tools, tracks concept mastery, and recommends the next best learning activity.

---

# 2. Current Project Summary

Everything currently lives under:

```text
intelligent-tutor/
├── jee_research/
├── jee_tutor_app/
├── papers/
└── outputs/
```

## 2.1 Research pipeline

The current research pipeline:

1. Creates a Python environment.
2. Downloads or loads JEE papers.
3. Extracts questions using PyMuPDF and regex.
4. Classifies subject, chapter, topic, difficulty, and type.
5. Produces corpus and trend-analysis files.
6. Generates Excel and Markdown reports.

The current corpus contains approximately:

- 6,567 total questions
- 3,097 Physics questions
- 2,186 Chemistry questions
- 1,284 Mathematics questions
- Papers from approximately 2016–2025
- Mostly single-answer MCQs
- A small number of integer-type questions

## 2.2 Current tutor application

The current application contains:

- FastAPI backend
- React and Vite frontend
- WebSocket tutoring
- Gemini-based response generation
- NetworkX curriculum graph
- JSON learner-memory persistence
- Question filtering
- Mastery dashboard
- D3 knowledge graph
- Pipeline visualization

## 2.3 Current tutoring flow

```text
Student message
    ↓
Load learner memory
    ↓
Resolve question context
    ↓
Classify request as PIPELINE or DIRECT
    ↓
Query graph and file store when required
    ↓
Build system prompt
    ↓
Generate Gemini response
    ↓
Update mastery from conversational signals
    ↓
Persist learner memory to JSON
```

This is a strong prototype architecture, but several parts are unsafe or unreliable for real learning.

---

# 3. Full Audit Findings

## 3.1 Corpus extraction is not sufficiently trustworthy

The current system depends heavily on regex-based question extraction. JEE papers can contain:

- Multiple columns
- Page headers and footers
- Equations
- Diagrams
- Tables
- Multi-line options
- Split questions across pages
- Section instructions
- Repeated numbering
- Scanned pages
- OCR errors
- Mathematical symbols that do not survive plain-text extraction

Possible consequences:

- Question boundaries may be wrong.
- Options may be attached to the wrong question.
- Formulas may be corrupted.
- Diagrams may be separated from their question.
- Answer keys may not be linked.
- Difficulty and chapter labels may be inaccurate.
- Questions may be duplicated.
- Some years or subjects may be underrepresented.

### Required correction

Every extracted question should carry source, confidence, and review metadata.

Recommended schema:

```json
{
  "question_id": "jee_main_2025_apr02_s1_q12",
  "paper_id": "jee_main_2025_apr02_shift1",
  "exam_type": "JEE_MAIN",
  "year": 2025,
  "session": "April",
  "shift": "Shift 1",
  "subject": "Physics",
  "chapter": "Work Energy and Power",
  "topic": "Work Energy Theorem",
  "question_number_in_paper": 12,
  "question_type": "MCQ_SINGLE",
  "stem_text": "A body of mass...",
  "stem_latex": "...",
  "options": [
    {"label": "A", "text": "..."},
    {"label": "B", "text": "..."},
    {"label": "C", "text": "..."},
    {"label": "D", "text": "..."}
  ],
  "correct_answer": "B",
  "official_solution": null,
  "page_number": 7,
  "question_bbox": [60, 140, 530, 610],
  "diagram_paths": [],
  "concept_ids": ["physics.work_energy_theorem"],
  "prerequisite_ids": ["physics.newtons_laws"],
  "difficulty": "MEDIUM",
  "extraction_confidence": 0.92,
  "classification_confidence": 0.87,
  "answer_key_confidence": 1.0,
  "review_status": "AUTO_VERIFIED",
  "source_pdf_hash": "...",
  "schema_version": "1.0"
}
```

## 3.2 Corpus cleaning can silently alter questions

Using an LLM to clean corrupted Unicode or mathematical text may change the original question.

Production risk:

- Numbers can change.
- Symbols can change.
- Negations can disappear.
- Formula meaning can change.
- Options can be reordered.
- Incorrect text can be accepted without review.

### Required correction

Never overwrite raw extraction.

Store:

```text
raw_text
normalized_text
correction_method
correction_model
correction_reason
confidence
human_review_status
```

Every transformation must remain reversible.

---

## 3.3 The current routing system is too simple

The current design uses two lanes:

- `PIPELINE`
- `DIRECT`

This is insufficient because a short message can still require retrieval or verification.

Example:

```text
"Is option B correct?"
```

This looks like a direct question, but answering safely requires:

1. Resolving the selected question.
2. Retrieving its answer key.
3. Checking the student's reasoning.
4. Verifying the final answer.
5. Updating mastery based on the attempt.

### Recommended intent types

```text
GREETING
CONCEPT_EXPLANATION
HINT_REQUEST
ANSWER_CHECK
FULL_SOLUTION
ERROR_EXPLANATION
DIAGNOSTIC_QUESTION
PRACTICE_REQUEST
QUESTION_SEARCH
REVISION_PLAN
PROGRESS_QUERY
OFF_TOPIC
```

The router should return structured output:

```json
{
  "intent": "ANSWER_CHECK",
  "question_id": "jee_main_2025_apr02_s1_q12",
  "subject": "Physics",
  "concept_ids": ["physics.work_energy_theorem"],
  "requires_retrieval": true,
  "requires_verification": true,
  "pedagogy_mode": "HINT_FIRST",
  "confidence": 0.94
}
```

---

## 3.4 The system behaves more like a chatbot than a tutor

A useful tutor should not immediately provide complete solutions for every question.

The current system needs explicit pedagogical behavior.

### Required tutoring modes

```text
LEARN
Explain a concept using examples and intuition.

HINT
Provide progressively stronger hints without revealing the answer immediately.

SOLVE
Provide a complete, verified solution.

CHECK
Evaluate the student's submitted answer or reasoning.

PRACTICE
Select or generate a suitable next question.

REVISE
Create a focused revision session using previously weak concepts.
```

### Recommended tutoring cycle

```text
Identify concept
    ↓
Estimate learner readiness
    ↓
Ask learner to attempt
    ↓
Analyze response
    ↓
Classify mistake
    ↓
Give smallest useful hint
    ↓
Ask for another attempt
    ↓
Reveal full solution only when needed
    ↓
Ask a related transfer question
    ↓
Schedule future revision
```

### Progressive hint ladder

```text
Hint Level 1
Recall the relevant principle.

Hint Level 2
Identify the formula or next reasoning step.

Hint Level 3
Show the setup, but not the final calculation.

Full Solution
Provide the complete verified derivation.
```

---

## 3.5 Current mastery tracking is invalid

The current system updates mastery using expressions such as:

```text
"I get it"      → positive mastery update
"confused"      → negative mastery update
tutor praise    → positive mastery update
```

This does not measure learning.

A student can say "I understand" while still being unable to solve a similar question. Tutor praise must never be treated as evidence of mastery.

### Evidence that should update mastery

```text
student answer correctness
partial-credit score
time taken
number of hints requested
highest hint level used
whether solution was revealed
confidence before answering
concepts tested
difficulty
repeat performance
performance after a delay
```

### Recommended initial model

Use Bayesian Knowledge Tracing, implemented locally.

For every concept, maintain:

```text
P_known
P_learn
P_guess
P_slip
P_forget
```

Recommended provisional mastery rule:

```text
P_known >= 0.85
AND at least 3 correct attempts
AND at least 1 correct attempt without major hints
AND at least 1 correct attempt after a delay
```

Do not begin with a deep neural knowledge-tracing model. The system does not yet have enough real learner-interaction data.

---

## 3.6 Current RAG design is inefficient

Attaching complete PDFs or large JSON files to every tutoring request causes:

- Higher latency
- Larger prompts
- Irrelevant context
- Conflicting sources
- Poor traceability
- Greater hallucination risk
- Unnecessary dependency on external file-search systems

### Required local retrieval pipeline

```text
Metadata filtering
    ↓
Keyword search
    ↓
Semantic vector search
    ↓
Merge results
    ↓
Rerank top candidates
    ↓
Expand one graph hop for prerequisites
    ↓
Return only the top evidence units
```

Each evidence unit should be question-level or concept-level, not a complete PDF.

### Recommended metadata filters

```text
exam_type
year
subject
chapter
topic
question_type
paper_id
question_id
has_diagram
review_status
```

### Recommended local technology

For the hackathon:

```text
SQLite FTS5 or PostgreSQL full-text search
FAISS or pgvector for embeddings
sentence-transformers for local embeddings
cross-encoder reranker for top candidates
```

Simplest hackathon option:

```text
SQLite + FTS5 + FAISS
```

More production-like local option:

```text
PostgreSQL + pgvector
```

For approximately 6,567 questions, either approach is sufficient.

---

## 3.7 Answers are not deterministically verified

An LLM should not be the only component responsible for correctness.

### Mathematics and Physics verification

Use:

```text
SymPy
NumPy
Pint
Restricted Python execution
Custom MCQ and integer validators
```

Possible checks:

- Algebraic equivalence
- Differentiation
- Integration
- Equation solving
- Numerical substitution
- Dimensional consistency
- Unit conversion
- Significant figures
- Option matching
- Matrix operations

### Chemistry verification

Use:

- Formula and reaction lookup from verified local notes
- Equation balancing
- Molecular-weight calculation
- Stoichiometric checks
- Periodic-table data
- NCERT-aligned local knowledge files
- Official answer-key validation

### Recommended answer pipeline

```text
Resolve question
    ↓
Retrieve verified source
    ↓
Generate candidate reasoning
    ↓
Extract calculations and claims
    ↓
Run deterministic tools
    ↓
Compare against official answer
    ↓
Run a second local verification prompt
    ↓
Return result with confidence
```

The system must be able to say:

```text
"I could not verify this answer reliably."
```

That is better than confidently returning an incorrect solution.

---

## 3.8 JSON learner-memory persistence is unsafe

Current per-session JSON files can cause:

- Data corruption
- Concurrent-write conflicts
- Lost progress
- Difficulty querying learner history
- Inability to support multiple backend workers
- No transaction safety
- No reliable migration path

### Local replacement

Use SQLite for the fastest hackathon implementation.

Recommended local persistence:

```text
SQLite
├── users
├── sessions
├── conversations
├── messages
├── attempts
├── mastery_states
├── misconceptions
├── review_schedule
└── model_runs
```

For a more production-like local setup, use PostgreSQL through Docker Compose.

### Recommendation

Use SQLite during the hackathon unless concurrent multi-user testing is required.

Use PostgreSQL when:

- Multiple students access the app simultaneously.
- Multiple FastAPI workers are used.
- More reliable transactional writes are needed.
- The team wants a direct future migration path.

---

## 3.9 Browser session IDs are not authentication

A browser-generated ID is not a secure identity system.

The application should use local authentication without Firebase or Auth0.

### Local authentication design

Use:

- Local username and password
- Password hashing with Argon2 or bcrypt
- JWT access tokens
- Refresh tokens stored in the local database
- Role-based access control
- Anonymous guest mode with optional account conversion

Recommended roles:

```text
STUDENT
TEACHER
ADMIN
```

For the hackathon, the minimum requirement is:

```text
guest session
student login
admin login
server-side ownership validation
```

The frontend must not be allowed to choose arbitrary learner IDs.

---

## 3.10 Startup performs too much work

The application currently loads questions, attaches images, syncs files, and builds the graph during startup.

This creates:

- Slow startup
- Duplicate work
- Failed deployments
- Inconsistent indexing
- Memory spikes
- Difficult debugging
- Unnecessary model/API calls

### Required correction

Startup should only:

```text
load configuration
connect to database
load already-built indexes
load already-built graph snapshot
start the API
```

All corpus processing should run as explicit commands:

```text
python -m tools.ingest
python -m tools.validate_corpus
python -m tools.build_embeddings
python -m tools.build_search_index
python -m tools.build_graph
```

---

## 3.11 Knowledge graph is too sparse

The current graph contains approximately:

- 58 chapter nodes
- 35 prerequisite edges
- 8 cross-domain scaffold edges

This is insufficient for reliable adaptive tutoring.

A chapter-level edge such as:

```text
Kinematics → Laws of Motion
```

is useful, but not enough.

The graph should include concept-level relationships.

### Recommended graph types

#### Curriculum graph

```text
concept → prerequisite concept
concept → related concept
concept → common misconception
concept → required mathematical skill
```

#### Question graph

```text
question → tests concept
question → requires concept
question → similar question
question → variant of question
```

#### Learner state

Store learner-concept mastery in the database instead of adding it as mutable graph nodes.

```text
student_id
concept_id
mastery_probability
attempt_count
last_practised_at
next_review_at
```

### Important production rule

Do not create new concepts dynamically in production.

Unknown concepts should be added to a review queue.

---

## 3.12 Frontend prioritizes architecture over student learning

The current pages include:

- Chat
- Questions
- Dashboard
- Graph
- Pipeline

The graph and pipeline pages are useful for demos, but they are not the highest-value student features.

### Recommended student navigation

```text
Today
Practice
Ask Tutor
Review Mistakes
Progress
```

### Recommended developer/admin navigation

```text
Corpus Audit
Knowledge Graph
Pipeline Trace
Model Runs
Evaluation
System Health
```

### Improved practice workspace

```text
Question panel
Answer workspace
Hint button
Formula panel
Timer
Confidence selector
Submit answer
Step-by-step feedback
Similar question
Bookmark
Report issue
```

### Improved progress dashboard

Show:

```text
strong concepts
weak concepts
recent mistakes
accuracy without hints
average solving time
upcoming revision
recommended next session
```

Avoid decorative mastery rings unless they show confidence and evidence count.

---

# 4. Target Zero-Cost Local Architecture

## 4.1 High-level architecture

```text
React + Vite Frontend
        │
        ▼
FastAPI API
        │
        ├── Local Authentication
        ├── Tutor Orchestrator
        ├── Retrieval Service
        ├── Verification Service
        ├── Mastery Service
        └── Analytics Service
        │
        ├── SQLite or PostgreSQL
        ├── FAISS or pgvector
        ├── Local filesystem or MinIO
        ├── NetworkX graph snapshot
        └── Local model server
                └── Ollama or llama.cpp
```

## 4.2 Recommended local stack

| Layer | Recommended local technology |
|---|---|
| Frontend | React + Vite |
| API | FastAPI |
| Database | SQLite for hackathon; PostgreSQL optional |
| Vector search | FAISS or pgvector |
| Keyword search | SQLite FTS5 or PostgreSQL full-text search |
| Local model serving | Ollama or llama.cpp |
| Tutor model | A local instruction model that fits available hardware |
| Embeddings | sentence-transformers |
| Reranker | Local cross-encoder |
| PDF extraction | PyMuPDF |
| OCR fallback | PaddleOCR or Tesseract |
| Layout extraction | Docling, PaddleOCR layout pipeline, or custom coordinate logic |
| Math verification | SymPy, NumPy, Pint |
| Graph | NetworkX |
| Password hashing | Argon2 or bcrypt |
| Streaming | Server-Sent Events |
| Background jobs | Python worker process or local Redis queue |
| Object storage | Local filesystem; MinIO optional |
| Logs | Python structured logging |
| Metrics | Prometheus optional |
| Packaging | Docker Compose |
| Testing | Pytest, Playwright, Locust |

## 4.3 Local model strategy

Do not hard-code the application to one model.

Create a model adapter:

```python
class LocalModelGateway:
    def classify_intent(self, payload): ...
    def generate_hint(self, payload): ...
    def generate_solution(self, payload): ...
    def verify_solution(self, payload): ...
    def summarize_progress(self, payload): ...
```

Support:

```text
Ollama
llama.cpp server
OpenAI-compatible local endpoints
mock model for tests
```

The selected model should be based on available hardware.

### Low-memory machine

Use a small quantized instruction model for:

- intent classification
- hint generation
- concise explanation
- misconception labeling

### Better local machine

Use a larger quantized model for:

- multi-step derivations
- answer comparison
- longer explanations
- chemistry reasoning

### Important restriction

The model should not directly access the entire corpus.

It receives:

```text
learner state
question
top retrieved evidence
verified answer key
available tools
pedagogy policy
response schema
```

---

# 5. Recommended Repository Structure

```text
intelligent-tutor/
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── dependencies/
│   └── web/
│       ├── src/
│       └── public/
│
├── core/
│   ├── tutor/
│   │   ├── orchestrator.py
│   │   ├── router.py
│   │   ├── pedagogy.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   ├── retrieval/
│   │   ├── keyword.py
│   │   ├── vector.py
│   │   ├── reranker.py
│   │   └── hybrid.py
│   ├── verification/
│   │   ├── math_tools.py
│   │   ├── physics_tools.py
│   │   ├── chemistry_tools.py
│   │   └── answer_checker.py
│   ├── mastery/
│   │   ├── bkt.py
│   │   ├── scheduler.py
│   │   └── misconceptions.py
│   ├── graph/
│   │   ├── curriculum.py
│   │   └── rag_context.py
│   ├── models/
│   │   ├── gateway.py
│   │   ├── ollama.py
│   │   └── mock.py
│   └── auth/
│       ├── passwords.py
│       ├── tokens.py
│       └── permissions.py
│
├── data/
│   ├── papers/
│   ├── corpus/
│   ├── images/
│   ├── indexes/
│   ├── graph/
│   └── app.db
│
├── pipelines/
│   ├── ingest_papers.py
│   ├── extract_questions.py
│   ├── validate_corpus.py
│   ├── build_embeddings.py
│   ├── build_search_index.py
│   └── build_graph.py
│
├── evaluation/
│   ├── gold_questions.jsonl
│   ├── corpus_eval.py
│   ├── retrieval_eval.py
│   ├── tutor_eval.py
│   └── mastery_eval.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker-compose.yml
├── Makefile
├── README.md
└── .env.example
```

---

# 6. Core Data Model

## 6.1 Users

```text
id
username
password_hash
role
created_at
last_login_at
```

## 6.2 Questions

```text
id
paper_id
subject
chapter
topic
question_type
stem_text
stem_latex
correct_answer
difficulty
page_number
review_status
extraction_confidence
classification_confidence
source_hash
```

## 6.3 Question options

```text
id
question_id
label
text
latex
```

## 6.4 Concepts

```text
id
subject
chapter
name
description
difficulty_level
```

## 6.5 Question concepts

```text
question_id
concept_id
relationship_type
weight
```

Relationship types:

```text
TESTS
REQUIRES
SUPPORTS
```

## 6.6 Attempts

```text
id
student_id
question_id
submitted_answer
is_correct
partial_credit
response_time_ms
hints_used
maximum_hint_level
solution_revealed
confidence_before_answer
created_at
```

## 6.7 Mastery state

```text
student_id
concept_id
p_known
attempt_count
correct_count
last_practised_at
next_review_at
updated_at
```

## 6.8 Misconceptions

```text
id
student_id
concept_id
misconception_type
evidence_attempt_id
confidence
status
created_at
```

## 6.9 Conversations

```text
id
student_id
question_id
mode
created_at
```

## 6.10 Messages

```text
id
conversation_id
role
content
model_name
prompt_version
verification_status
created_at
```

---

# 7. Tutor Orchestration Design

## 7.1 Input

```json
{
  "student_id": "student_123",
  "conversation_id": "conv_456",
  "question_id": "jee_main_2025_apr02_s1_q12",
  "message": "I used conservation of energy and got option C.",
  "mode": "CHECK"
}
```

## 7.2 Orchestration steps

```text
1. Validate authenticated student
2. Load question
3. Load learner mastery for related concepts
4. Classify intent
5. Parse student attempt
6. Retrieve official source and related concept notes
7. Run deterministic checks
8. Select tutoring policy
9. Generate response
10. Verify generated response
11. Save conversation and attempt
12. Update mastery
13. Update revision schedule
14. Stream response to frontend
```

## 7.3 Tutor response schema

```json
{
  "message": "Your energy equation is correct, but the final height substitution is incorrect.",
  "intent": "ANSWER_CHECK",
  "verification_status": "VERIFIED",
  "hint_level": 1,
  "concepts": ["physics.work_energy_theorem"],
  "next_action": "TRY_AGAIN",
  "mastery_update_allowed": true,
  "source_question_id": "jee_main_2025_apr02_s1_q12"
}
```

Structured responses prevent the model from controlling application state directly.

---

# 8. Local Retrieval Design

## 8.1 Indexing unit

Index each question separately.

Also create separate concept-note documents.

```text
Question document
Concept note
Worked example
Common misconception
Formula reference
```

## 8.2 Search pipeline

```text
Query normalization
    ↓
Subject/chapter filter
    ↓
SQLite FTS5 keyword search
    ↓
FAISS semantic search
    ↓
Reciprocal-rank merge
    ↓
Cross-encoder rerank
    ↓
Top 3–5 evidence units
```

## 8.3 Suggested local embedding flow

```python
text = "\n".join([
    question.subject,
    question.chapter,
    question.topic,
    question.stem_text,
    " ".join(option.text for option in question.options)
])

vector = embedding_model.encode(text, normalize_embeddings=True)
```

Store:

```text
question_id
embedding
embedding_model
embedding_version
corpus_version
```

## 8.4 Retrieval acceptance criteria

For a manually reviewed test set:

```text
Recall@5 >= 0.90
MRR >= 0.75
Correct question retrieved for direct question lookup
No unreviewed corpus item used for verified answers
```

---

# 9. Verification Framework

## 9.1 Verification statuses

```text
VERIFIED
PARTIALLY_VERIFIED
UNVERIFIED
CONFLICTING_SOURCE
TOOL_FAILURE
```

## 9.2 Mathematics verifier

Functions:

```text
simplify_expression
compare_expressions
solve_equation
differentiate
integrate
evaluate_numeric
check_matrix_result
match_mcq_option
```

## 9.3 Physics verifier

Functions:

```text
check_dimensions
convert_units
evaluate_formula
check_sign
check_vector_components
validate_numeric_tolerance
match_option
```

## 9.4 Chemistry verifier

Functions:

```text
balance_equation
compute_molar_mass
check_stoichiometry
check_oxidation_state
validate_formula
lookup_verified_fact
```

## 9.5 LLM verifier

A second local model call may review:

```text
Does the explanation match the verified answer?
Are any calculation steps unsupported?
Does the response reveal too much for the selected hint level?
Does it cite a source not present in the evidence?
```

The second model is an additional check, not a replacement for deterministic verification.

---

# 10. Adaptive Learning and Revision

## 10.1 Concept mastery update

Mastery should update only after an attempt event.

Inputs:

```text
correctness
difficulty
hint usage
time taken
solution revealed
attempt spacing
confidence
```

Example interpretation:

```text
Correct without hints
Strong positive evidence

Correct after one hint
Moderate positive evidence

Correct after full solution
Minimal positive evidence

Incorrect but logically structured
Useful misconception evidence

Fast incorrect answer with high confidence
Strong misconception evidence
```

## 10.2 Spaced revision

Each concept receives:

```text
last_practised_at
next_review_at
review_interval
recent_accuracy
mastery_probability
```

Simple local scheduler:

```text
New concept       → review in 1 day
Weak concept      → review in 1 day
Improving concept → review in 3 days
Stable concept    → review in 7 days
Mastered concept  → review in 14–30 days
```

## 10.3 Next-question selection

Score candidate questions using:

```text
concept weakness
prerequisite readiness
difficulty fit
recent exposure
question diversity
exam relevance
hint dependence
revision urgency
```

Example:

```text
candidate_score =
    0.30 * concept_need
  + 0.20 * revision_urgency
  + 0.15 * difficulty_fit
  + 0.15 * prerequisite_readiness
  + 0.10 * exam_relevance
  + 0.10 * diversity
```

---

# 11. Frontend Product Design

## 11.1 Today page

Show:

```text
Today's 20-minute plan
Questions due for revision
Current weak concepts
Continue previous session
```

## 11.2 Practice page

Features:

```text
subject filter
chapter filter
difficulty filter
timed mode
practice mode
adaptive mode
answer input
confidence selector
hint ladder
solution review
next question
```

## 11.3 Ask Tutor page

Features:

```text
free-form tutoring
question-aware chat
concept explanation
step checking
formula explanation
diagram-aware context
```

## 11.4 Review Mistakes page

Show:

```text
recent incorrect questions
misconception type
student's previous answer
correct reasoning
similar retry question
```

## 11.5 Progress page

Show:

```text
mastery by concept
accuracy without hints
average solving time
revision completion
strongest topics
weakest topics
recent improvement
```

## 11.6 Admin and demo pages

Keep:

```text
knowledge graph
pipeline visualization
retrieval trace
model trace
corpus audit
evaluation dashboard
```

These should not be the main student experience.

---

# 12. Local Security Design

## 12.1 Authentication

Use:

```text
username
password
Argon2 password hash
JWT access token
refresh token
role
```

## 12.2 Authorization

Every request must check:

```text
authenticated user
requested student ownership
role permissions
question access
conversation ownership
```

## 12.3 Local secrets

Store in `.env`:

```text
JWT_SECRET
DATABASE_URL
MODEL_BASE_URL
MODEL_NAME
EMBEDDING_MODEL_PATH
DATA_DIRECTORY
```

Never commit `.env`.

Provide `.env.example`.

## 12.4 Input controls

Add:

```text
maximum message length
maximum uploaded file size
allowed file extensions
rate limiting
HTML sanitization
LaTeX sanitization
path traversal prevention
safe subprocess execution
restricted Python tools
```

## 12.5 Safe local tool execution

Never execute raw model-generated Python.

Expose only approved functions:

```python
TOOLS = {
    "solve_equation": solve_equation,
    "differentiate": differentiate,
    "check_units": check_units,
    "balance_equation": balance_equation
}
```

---

# 13. Evaluation Plan

## 13.1 Corpus evaluation

Measure:

```text
question-boundary precision
question-boundary recall
option extraction accuracy
formula preservation accuracy
diagram association accuracy
answer-key linkage accuracy
subject classification macro-F1
chapter classification macro-F1
duplicate rate
low-confidence rate
```

## 13.2 Retrieval evaluation

Measure:

```text
Recall@5
MRR
nDCG@10
question lookup accuracy
concept-note retrieval accuracy
diagram retrieval accuracy
```

## 13.3 Tutor evaluation

Create a teacher-reviewed gold set.

Measure:

```text
final-answer correctness
step correctness
hint usefulness
hint leakage
source faithfulness
unsupported claims
misconception diagnosis accuracy
pedagogy compliance
```

## 13.4 Mastery evaluation

Measure:

```text
next-response prediction accuracy
Brier score
false-mastery rate
mastery calibration
delayed-retention accuracy
```

## 13.5 System evaluation

Measure:

```text
time to first token
complete-response latency
retrieval latency
verification latency
local memory usage
CPU usage
GPU usage
concurrent active students
stream reconnect success
error rate
```

---

# 14. Ten-Phase Implementation Plan

The implementation is divided into ten phases. Each phase should end with a working, demonstrable checkpoint.

---

## Phase 1 — Freeze Scope and Establish Baseline

### Goal

Create a reproducible baseline before changing architecture.

### Tasks

- Freeze the current corpus.
- Create a Git tag for the existing prototype.
- Record current extraction statistics.
- Record current response latency.
- Record current question and graph counts.
- Create a manually reviewed sample of at least 100 questions.
- Include Physics, Chemistry, Mathematics, MCQ, integer, and diagram questions.
- Define the final local deployment hardware.
- Select SQLite or PostgreSQL.
- Select FAISS or pgvector.
- Select the local model runtime.
- Add `.env.example`.
- Add a single setup command.

### Deliverables

```text
baseline_report.md
gold_questions.jsonl
hardware_profile.md
.env.example
Makefile
```

### Verification checkpoint

```text
Application starts locally
Existing corpus is reproducible
100-question gold set exists
Baseline metrics are recorded
```

---

## Phase 2 — Build a Trustworthy Corpus Pipeline

### Goal

Improve question extraction and make every transformation traceable.

### Tasks

- Add source-PDF hashing.
- Preserve page numbers and bounding boxes.
- Separate raw and normalized text.
- Reconstruct multi-line options.
- Extract diagrams as image crops.
- Link diagrams to questions.
- Add question-level confidence.
- Add duplicate detection.
- Add answer-key linkage.
- Add review states.
- Prevent automatic overwriting by cleanup scripts.
- Create validation reports.
- Reprocess only changed papers.

### Deliverables

```text
corpus_v2.jsonl
corpus_validation_report.md
extraction_errors.jsonl
review_queue.jsonl
diagram_index.jsonl
```

### Verification checkpoint

```text
At least 95% of gold questions have correct boundaries
At least 95% of gold options are correctly attached
All raw text remains recoverable
Every question has source metadata
```

---

## Phase 3 — Introduce Local Persistence and Authentication

### Goal

Replace JSON learner memory and browser-controlled identity.

### Tasks

- Create database schema.
- Add local user registration.
- Add local login.
- Hash passwords.
- Issue JWT access tokens.
- Add student, teacher, and admin roles.
- Add anonymous guest mode.
- Migrate learner memory into database tables.
- Add conversation and message persistence.
- Add attempt persistence.
- Enforce student ownership in backend routes.
- Add database migrations.

### Deliverables

```text
database schema
migration scripts
auth routes
protected routes
guest-to-student migration
```

### Verification checkpoint

```text
Student progress survives browser restart
One student cannot access another student's data
Concurrent writes do not corrupt learner state
No learner JSON files are used
```

---

## Phase 4 — Build Local Hybrid Retrieval

### Goal

Replace full-file attachment with question-level retrieval.

### Tasks

- Create keyword index.
- Generate local embeddings.
- Create vector index.
- Add metadata filters.
- Add reciprocal-rank fusion.
- Add local reranker.
- Add question-level source references.
- Add concept-note documents.
- Add retrieval caching.
- Create retrieval evaluation set.
- Remove runtime dependency on external file-search systems.

### Deliverables

```text
keyword index
vector index
retrieval service
reranker
retrieval benchmark
```

### Verification checkpoint

```text
Recall@5 is at least 0.90 on the reviewed benchmark
Question lookup returns the exact source
Only top evidence units are sent to the model
No complete PDF is attached to ordinary tutoring requests
```

---

## Phase 5 — Create the Tutor Orchestrator

### Goal

Replace direct chatbot calls with a controlled tutoring workflow.

### Tasks

- Implement structured intent classification.
- Add tutoring modes.
- Add pedagogy-policy selection.
- Add hint-level tracking.
- Add question-context resolution.
- Add learner-state loading.
- Add structured tutor-response schema.
- Add local model gateway.
- Add mock-model adapter for tests.
- Add prompt versioning.
- Add response-streaming events.
- Move model calls out of `server.py`.

### Deliverables

```text
TutorOrchestrator
IntentRouter
PedagogyPolicy
LocalModelGateway
structured response schemas
```

### Verification checkpoint

```text
Every tutor response has an intent
Every response has a verification status
Hint mode does not reveal the final answer immediately
Answer-check mode always resolves the question
Application can run with a mock model during tests
```

---

## Phase 6 — Add Deterministic Verification

### Goal

Make answers reliable enough for educational use.

### Tasks

- Add SymPy expression comparison.
- Add equation-solving tools.
- Add differentiation and integration tools.
- Add numerical evaluators.
- Add dimensional-analysis support.
- Add MCQ option matching.
- Add chemistry calculators.
- Add official-answer comparison.
- Add tool-call logging.
- Add answer confidence.
- Add safe failure behavior.
- Add second-pass local response verification.

### Deliverables

```text
math verifier
physics verifier
chemistry verifier
answer checker
verification report
```

### Verification checkpoint

```text
All gold-set numeric answers are checked by tools
Wrong model answers are blocked or marked unverified
Tool failures do not crash the tutoring session
The model cannot execute arbitrary code
```

---

## Phase 7 — Implement Mastery, Misconceptions, and Revision

### Goal

Track learning from actual evidence.

### Tasks

- Implement Bayesian Knowledge Tracing.
- Map each question to one or more concepts.
- Update mastery only after attempt events.
- Store hint usage.
- Store time taken.
- Store confidence before answering.
- Add misconception categories.
- Add revision scheduling.
- Add next-question scoring.
- Add prerequisite checks.
- Add minimum-evidence rules before showing mastery.
- Add teacher-readable learner summaries.

### Deliverables

```text
BKT engine
mastery service
misconception classifier
revision scheduler
adaptive question selector
```

### Verification checkpoint

```text
Saying "I understand" does not change mastery
Correct attempts update related concepts
Hint-heavy attempts contribute less evidence
Weak concepts are scheduled for review
Next-question recommendations are explainable
```

---

## Phase 8 — Redesign the Student Experience

### Goal

Turn the prototype into a useful tutoring product.

### Tasks

- Create Today page.
- Create Practice page.
- Improve Ask Tutor.
- Create Review Mistakes page.
- Rebuild Progress page.
- Add confidence input.
- Add hint ladder.
- Add attempt submission.
- Add retry question.
- Add formula rendering.
- Add diagram rendering.
- Add loading and failure states.
- Move Graph and Pipeline pages into Admin/Demo.
- Add responsive layout.

### Deliverables

```text
Today page
Practice workspace
Tutor page
Mistake review page
Progress page
Admin demo pages
```

### Verification checkpoint

```text
A student can complete a full practice session
A student can request progressive hints
A student can retry a weak concept
Progress reflects attempt evidence
The main navigation is learning-focused
```

---

## Phase 9 — Evaluation, Testing, and Local Performance

### Goal

Make the system measurable and stable.

### Tasks

- Add unit tests.
- Add integration tests.
- Add end-to-end tests.
- Add corpus evaluation.
- Add retrieval evaluation.
- Add tutor gold-set evaluation.
- Add load testing.
- Add local memory profiling.
- Add response-latency tracking.
- Add model-failure tests.
- Add database backup and restore.
- Add structured logs.
- Add health endpoints.
- Add offline evaluation command.

### Deliverables

```text
pytest suite
Playwright tests
Locust scenarios
evaluation report
performance report
backup script
```

### Verification checkpoint

```text
Critical flows pass end-to-end
Retrieval metrics meet threshold
Gold-set tutor correctness is reported
Application survives model timeout
Database can be restored from backup
```

---

## Phase 10 — Package the Hackathon Demo

### Goal

Provide a one-command local deployment and a convincing demonstration.

### Tasks

- Add Docker Compose.
- Add local model setup instructions.
- Add a lightweight fallback mode.
- Add sample users.
- Add seed data.
- Add one-command startup.
- Add one-command evaluation.
- Add demo script.
- Add architecture diagram.
- Add system limitations.
- Add future-production roadmap.
- Record a fallback demo video.
- Create a five-minute judge flow.

### Deliverables

```text
docker-compose.yml
README.md
demo_script.md
architecture_diagram
sample credentials
seed command
evaluation command
```

### Verification checkpoint

```text
Fresh machine can start the application locally
No paid API key is required
No Firebase or Auth0 dependency exists
Core demo works without internet
Judges can see retrieval, verification, mastery, and adaptive practice
```

---

# 15. Recommended Hackathon Demo Flow

A strong five-minute demonstration:

## Step 1 — Student opens Today

Show:

```text
Weak concept: Work Energy Theorem
Due revision: 3 questions
Recommended session: 15 minutes
```

## Step 2 — Student attempts a question

The student chooses an incorrect answer with high confidence.

## Step 3 — Tutor diagnoses the error

The tutor identifies:

```text
misconception: confusing force with work
```

It provides Hint Level 1 rather than the full answer.

## Step 4 — Student retries

The student submits a corrected equation.

The deterministic verifier checks the equation with SymPy or numerical tools.

## Step 5 — Tutor confirms the reasoning

The response shows:

```text
verification status: VERIFIED
source: JEE Main 2022
concept: Work Energy Theorem
```

## Step 6 — Mastery updates

The dashboard shows:

```text
mastery increased
hint dependence recorded
revision scheduled
```

## Step 7 — Adaptive next question

The system recommends a related but slightly different question.

## Step 8 — Admin pipeline view

Show:

```text
intent
retrieved evidence
tool verification
pedagogy policy
mastery event
```

This demonstrates real system intelligence rather than only a generated chat response.

---

# 16. Minimum Viable Hackathon Scope

If time is limited, prioritize these features:

```text
1. Clean 300-question verified corpus
2. Local authentication
3. SQLite persistence
4. FAISS retrieval
5. Local model through Ollama
6. Hint, Check, and Solve modes
7. SymPy verification for Mathematics and Physics
8. Attempt-based mastery
9. Adaptive next-question selection
10. One-command local startup
```

Do not attempt to perfect all 6,567 questions during the hackathon.

A smaller verified corpus is more valuable than a large unreliable corpus.

Recommended demo subset:

```text
100 Physics questions
100 Chemistry questions
100 Mathematics questions
20 diagram questions
20 integer questions
teacher-reviewed answers
concept mappings
difficulty labels
```

---

# 17. Features to Defer Until After the Hackathon

Defer:

```text
voice tutoring
multi-institution tenancy
teacher classroom management
large-scale analytics
mobile applications
real-time collaboration
full JEE paper generation
automatic concept creation
deep knowledge tracing
large graph databases
distributed microservices
Kubernetes
hosted vector databases
paid LLM APIs
```

These features increase complexity without improving the core demonstration.

---

# 18. Final Acceptance Criteria

The hackathon build is successful when:

## Corpus

```text
A reviewed corpus subset exists
Questions preserve formulas and diagrams
Every question has source metadata
Every answer has confidence or review status
```

## Tutor

```text
The tutor supports Hint, Check, Solve, Learn, and Practice
The tutor does not reveal full solutions in Hint mode
The tutor uses retrieved evidence
The tutor returns verification status
```

## Verification

```text
Math and Physics calculations use deterministic tools
Official answer keys are compared
Unverified answers are clearly marked
Arbitrary model-generated code is never executed
```

## Learning

```text
Mastery changes only after attempts
Hint usage affects evidence strength
Misconceptions are recorded
Revision is scheduled
Next-question recommendations are explainable
```

## Engineering

```text
The system starts locally
No paid API is required
No Firebase dependency exists
No Auth0 dependency exists
No hosted database is required
No hosted file store is required
No cloud deployment is required
```

## Demonstration

```text
The full learning loop can be demonstrated in under five minutes
The admin view can show retrieval and verification traces
The application works without internet after models and dependencies are installed
```

---

# 19. Final Product Positioning

Do not position the application as:

> "A chatbot trained on JEE papers."

Position it as:

> "A verified adaptive JEE tutoring system that diagnoses mistakes, provides progressive hints, validates solutions using mathematical tools, tracks concept mastery, and selects the next best practice activity."

The strongest differentiators are:

```text
verified question corpus
deterministic answer checking
progressive hints
attempt-based mastery
misconception detection
adaptive revision
fully local deployment
zero recurring infrastructure cost
student-data privacy
```

This direction makes the project more credible as an educational product and more defensible as a hackathon submission.
