import os
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

# Load .env variables (GOOGLE_API_KEY etc.) before any Google SDK initialisation
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types


# Import our customized NetworkX Graph Manager
from graph import KnowledgeGraphManager

# Resolve the frontend directory relative to this file
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ══════════════════════════════════════════════════════════════
#  LOGGING CONFIGURATION
# ══════════════════════════════════════════════════════════════
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(),                          # Console
        logging.FileHandler("jee_tutor.log", encoding="utf-8"),  # File log
    ]
)

# Silence overly verbose third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("google").setLevel(logging.WARNING)

logger        = logging.getLogger("tutor.server")
logger_boot   = logging.getLogger("tutor.boot")
logger_api    = logging.getLogger("tutor.api")
logger_ws     = logging.getLogger("tutor.websocket")
logger_intent = logging.getLogger("tutor.intent")
logger_graph  = logging.getLogger("tutor.graph")

# ══════════════════════════════════════════════════════════════
#  APPLICATION SETUP
# ══════════════════════════════════════════════════════════════
app = FastAPI(title="JEE Intelligent Tutor Backend Engine")

# --- CORS POLICY — allow both dev-server and file:// origins ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Permit file:// (null origin) + any localhost port
    allow_credentials=False,       # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve the frontend static files (css/, js/ subdirectories + assets) ──
# This mounts the entire frontend/ directory at /static so that the browser
# can fetch css/styles.css and js/**/*.jsx via HTTP from the same origin.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info(f"Frontend static files mounted from: {FRONTEND_DIR}")
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR} — static files will not be served.")

IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "jee_research" / "extracted" / "images"
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
    logger.info(f"Images mounted from: {IMAGES_DIR}")
else:
    logger.warning(f"Images directory not found at {IMAGES_DIR}")

# --- GLOBAL MEMORY STACKS ---
QUESTIONS_RAM: List[dict] = []
QUESTIONS_FILE_PATH = str(Path(__file__).resolve().parent / "jee_corpus.json")
PAPERS_CORPUS_DIR = str(Path(__file__).resolve().parent.parent / "papers")


# --- PYDANTIC CONTRACT SCHEMAS ---
class ChatPayload(BaseModel):
    session_id: str
    student_message: str
    question_id: Optional[str] = None
    chapter_context: Optional[str] = None
    chat_history: List[dict] = []


# ══════════════════════════════════════════════════════════════
#  PHASE 1 BOOT: LOAD QUESTIONS INTO RAM
# ══════════════════════════════════════════════════════════════
def load_questions_into_ram():
    global QUESTIONS_RAM
    logger_boot.info(f"Loading question corpus from '{QUESTIONS_FILE_PATH}'...")
    if os.path.exists(QUESTIONS_FILE_PATH):
        try:
            with open(QUESTIONS_FILE_PATH, "r", encoding="utf-8") as f:
                QUESTIONS_RAM = json.load(f)
            
            # Attach images to questions
            images_dir = Path(__file__).resolve().parent.parent.parent / "jee_research" / "extracted" / "images"
            if images_dir.exists():
                for q in QUESTIONS_RAM:
                    q["images"] = []
                    paper_filename = q.get("paper_filename", "")
                    q_num = q.get("question_number")
                    if paper_filename and q_num is not None:
                        paper_basename = paper_filename.replace(".pdf", "")
                        q_dir = images_dir / paper_basename
                        if q_dir.exists():
                            prefix = f"img_{q_num}_"
                            try:
                                imgs = [f for f in os.listdir(q_dir) if f.startswith(prefix)]
                                imgs.sort()
                                for img in imgs:
                                    img_path = q_dir / img
                                    # Skip the known 63KB watermark/logo image
                                    if img_path.stat().st_size == 63492:
                                        continue
                                    q["images"].append(f"/images/{paper_basename}/{img}")
                            except Exception as e:
                                logger_boot.warning(f"Error reading images for Q{q_num}: {e}")

            logger_boot.info(f"✅ Loaded {len(QUESTIONS_RAM):,} questions into RAM.")
        except Exception as e:
            logger_boot.critical(f"❌ Critical failure reading Question Bank: {e}", exc_info=True)
            QUESTIONS_RAM = []
    else:
        logger_boot.warning(f"⚠️  Question bank file '{QUESTIONS_FILE_PATH}' not found on disk.")


# ══════════════════════════════════════════════════════════════
#  PHASE 2 BOOT: GOOGLE FILE SEARCH STORE SYNC
# ══════════════════════════════════════════════════════════════
async def synchronize_file_search_store():
    """Audits and mounts Layer 4 reference assets into the Gemini File Store."""
    logger_boot.info("Indexing multimodal reference materials into Google File Search Store...")
    client = genai.Client()

    existing_files = {f.display_name: f.name for f in client.files.list()}
    logger_boot.debug(f"Found {len(existing_files)} files already cached in Google File Store.")
    app.state.file_store_registry = {}

    if not os.path.exists(PAPERS_CORPUS_DIR):
        logger_boot.warning(f"⚠️  Corpus folder '{PAPERS_CORPUS_DIR}' not found — skipping asset registration.")
        return

    supported_extensions = (".pdf", ".json")
    uploaded_count = 0
    cached_count = 0

    for root, _, files in os.walk(PAPERS_CORPUS_DIR):
        for file in files:
            if file.endswith(supported_extensions):
                local_path = os.path.join(root, file)
                if file in existing_files:
                    logger_boot.debug(f"   [CACHE HIT ] {file}")
                    app.state.file_store_registry[file] = existing_files[file]
                    cached_count += 1
                else:
                    try:
                        logger_boot.info(f"   [UPLOADING ] {file} ...")
                        uploaded_artifact = client.files.upload(file=local_path)
                        app.state.file_store_registry[file] = uploaded_artifact.name
                        logger_boot.info(f"   [UPLOADED  ] {file} → {uploaded_artifact.name}")
                        uploaded_count += 1
                    except Exception as upload_error:
                        logger_boot.error(f"   [FAILED    ] {file}: {upload_error}", exc_info=True)

    logger_boot.info(
        f"✅ File Store synced — {cached_count} cached, {uploaded_count} uploaded, "
        f"{len(app.state.file_store_registry)} total active mappings."
    )


# ══════════════════════════════════════════════════════════════
#  STARTUP EVENT
# ══════════════════════════════════════════════════════════════
@app.on_event("startup")
async def boot_sequence():
    logger_boot.info("=" * 60)
    logger_boot.info("🚀  JEE Intelligent Tutor — Boot Sequence Starting")
    logger_boot.info(f"    Timestamp : {datetime.now().isoformat()}")
    logger_boot.info("=" * 60)

    load_questions_into_ram()
    import asyncio
    asyncio.create_task(synchronize_file_search_store())

    logger_graph.info("Initialising Knowledge Graph Manager...")
    app.state.graph = KnowledgeGraphManager()
    if QUESTIONS_RAM:
        logger_graph.info(f"Linking {len(QUESTIONS_RAM):,} questions to graph nodes...")
        app.state.graph.link_questions(QUESTIONS_RAM)

    logger_boot.info("=" * 60)
    logger_boot.info("✅  Boot sequence complete — ready for connections.")
    logger_boot.info("=" * 60)


# ══════════════════════════════════════════════════════════════
#  REST ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the React SPA index.html at the root URL."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return {"error": "Frontend not found. Run the app from the jee_tutor_app directory."}


@app.get("/questions")
async def get_questions(
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10000, ge=1, le=10000)
):
    """In-memory filtering and chunked pagination over the question corpus."""
    logger_api.debug(f"GET /questions — subject={subject!r}, chapter={chapter!r}, page={page}, limit={limit}")

    filtered = QUESTIONS_RAM
    if subject:
        filtered = [q for q in filtered if q.get("subject", "").lower() == subject.lower()]
    if chapter and chapter.lower() != "all chapters":
        filtered = [q for q in filtered if q.get("chapter", "").lower() == chapter.lower()]

    # Sort by subject, then year, then difficulty
    filtered.sort(key=lambda x: (
        x.get("subject", ""),
        int(x.get("year") or 0),
        {"Easy": 1, "Medium": 2, "Hard": 3}.get(x.get("difficulty"), 4)
    ))

    start_idx = (page - 1) * limit
    end_idx   = start_idx + limit
    result    = filtered[start_idx:end_idx]

    logger_api.debug(f"  → Returning {len(result)} of {len(filtered)} filtered questions.")
    return {
        "total_matches": len(filtered),
        "page":  page,
        "limit": limit,
        "questions": result
    }


@app.get("/chapters")
async def get_chapters():
    """Returns predefined canonical chapters grouped by subject from the Knowledge Graph."""
    logger_api.debug("GET /chapters")
    buckets: dict = {"Physics": [], "Chemistry": [], "Mathematics": []}
    for node, data in app.state.graph.G.nodes(data=True):
        if data.get("type") == "chapter":
            subj = data.get("subject", "General")
            if subj in buckets:
                buckets[subj].append(node)
                
    for k in buckets:
        buckets[k].sort()
    return buckets


@app.get("/memory/{session_id}")
async def get_learner_dashboard_memory(session_id: str):
    """Exposes learner mastery matrix for graph tracking."""
    logger_api.debug(f"GET /memory/{session_id}")
    return app.state.graph.get_learner_memory(session_id)


@app.get("/graph")
async def get_knowledge_graph_topology():
    """Serves full NetworkX link topology for the concept map frontend."""
    logger_api.debug("GET /graph")
    return app.state.graph.export_subgraph()


@app.get("/stats/{session_id}")
async def get_learner_stats(session_id: str):
    """Dashboard summary: subject averages, adaptive next concepts, misconceptions."""
    logger_api.debug(f"GET /stats/{session_id}")
    memory  = app.state.graph.get_learner_memory(session_id)
    mastery = memory.get("mastery", {})

    # Compute hierarchical averages: Concept -> Chapter -> Subject
    G = app.state.graph.G
    
    chapter_concepts = {}
    subject_chapters = {"Physics": [], "Chemistry": [], "Mathematics": []}
    
    for node, data in G.nodes(data=True):
        if data.get("type") == "chapter":
            subj = data.get("subject", "General")
            if subj in subject_chapters:
                subject_chapters[subj].append(node)
            if node not in chapter_concepts:
                chapter_concepts[node] = []
        elif data.get("type") == "concept":
            parent = data.get("parent_chapter")
            if parent:
                if parent not in chapter_concepts:
                    chapter_concepts[parent] = []
                chapter_concepts[parent].append(node)
                
    chapter_mastery = {}
    for chapter, concepts in chapter_concepts.items():
        if not concepts:
            chapter_mastery[chapter] = mastery.get(chapter, 0.0)
        else:
            total = sum(mastery.get(c, 0.0) for c in concepts)
            chapter_mastery[chapter] = total / len(concepts)
            
    subject_averages = {}
    for subj, chapters in subject_chapters.items():
        if not chapters:
            subject_averages[subj] = 0.0
        else:
            total = sum(chapter_mastery[c] for c in chapters)
            subject_averages[subj] = round(total / len(chapters), 2)


    return {
        "session_id":       session_id,
        "mastery":          mastery,
        "misconceptions":   memory.get("misconceptions", {}),
        "session_count":    len(memory.get("session_history", [])),
        "subject_averages": subject_averages,
        "subject_chapters": subject_chapters,
        "chapter_mastery":  chapter_mastery,
        "next_concepts": {
            "Physics":     app.state.graph.get_adaptive_next_concept(session_id, "Physics"),
            "Chemistry":   app.state.graph.get_adaptive_next_concept(session_id, "Chemistry"),
            "Mathematics": app.state.graph.get_adaptive_next_concept(session_id, "Mathematics"),
        },
    }


@app.get("/adaptive/{session_id}")
async def get_adaptive_path(session_id: str, subject: Optional[str] = None):
    """Returns the next recommended concept for the learner in a given subject."""
    logger_api.debug(f"GET /adaptive/{session_id} subject={subject}")
    return {
        "session_id": session_id,
        "next_concept": app.state.graph.get_adaptive_next_concept(session_id, subject or ""),
    }


# ══════════════════════════════════════════════════════════════
#  INTENT CLASSIFIER
# ══════════════════════════════════════════════════════════════
def run_intent_classifier(student_msg: str) -> str:
    """Lightweight decision block mapping queries to PIPELINE or DIRECT lanes."""
    logger_intent.debug(f"Classifying intent for: '{student_msg[:80]}...'")
    client = genai.Client()
    prompt = f"""
    Analyze the following Indian JEE student message and classify its routing path.
    Respond with exactly one word: either 'PIPELINE' or 'DIRECT'.

    Lanes:
    - 'PIPELINE': Triggered if they ask to solve a problem, need a derivation, want a hint, require step-by-step math breakdowns, or request deep technical explanations of physics/chemistry/math concepts.
    - 'DIRECT': Triggered if it is conversational banter, basic greeting, checking an answer choice option (e.g., 'Is option B right?'), quick simple confirmation, or motivation.

    Student Message: "{student_msg}"
    Classification Lane:"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        decision = response.text.strip().upper()
        lane = "PIPELINE" if "PIPELINE" in decision else "DIRECT"
        logger_intent.info(f"Intent classified → {lane}  (raw='{response.text.strip()}')")
        return lane
    except Exception as e:
        logger_intent.error(f"Intent classification failed: {e} — defaulting to DIRECT", exc_info=True)
        return "DIRECT"


def get_local_socratic_fallback(target_q, student_message, active_concept_node, active_chapter, active_subject):
    msg_lower = student_message.lower()
    
    header = "⚠️ [System Notice: Gemini API rate limit reached. Running local Socratic backup mode]\n\n"
    
    if msg_lower.startswith("please help me solve this question") and target_q:
        q_text = target_q.get("raw_text", "")
        snippet = q_text[:200] + "..." if len(q_text) > 200 else q_text
        
        return (
            header +
            f"**Option A - Let me break this down step by step:**\n"
            f"Let's look at this **{active_subject}** problem under the concept of **{active_chapter}**.\n"
            f"Question:\n> {snippet}\n\n"
            f"To get started, what are the primary variables or physical quantities given in the question, and what are we trying to calculate?\n\n"
            f"**Option B - Build your intuition with practice questions:**\n"
            f"Here are three adaptive practice questions for **{active_concept_node}**:\n"
            f"1. **Easy**: A basic conceptual question testing the definition and core units.\n"
            f"2. **Medium**: A standard problem with numerical application similar to the active question.\n"
            f"3. **Hard**: An advanced question combining multiple concepts from {active_chapter}.\n\n"
            f"Reply A to work through this problem together, or B to start with practice questions."
        )
    
    elif msg_lower == "a":
        return (
            header +
            f"Excellent! Let's work through the active question step by step.\n\n"
            f"Step 1: Based on the question context, what is the formula or physical law that relates these quantities? (For example, Ohm's law, Faraday's law, or equations of motion?)\n\n"
            f"Give it a try and type your formula or thoughts!"
        )
    elif msg_lower == "b":
        return (
            header +
            f"Awesome, let's build your intuition with practice questions first!\n\n"
            f"Let's start with the **Easy** foundational question:\n"
            f"> What is the fundamental unit of measurement/relation for {active_concept_node}?\n\n"
            f"Type your answer, and I'll confirm if it's correct!"
        )
    else:
        return (
            header +
            f"Thank you for your response! Let's examine that approach. \n\n"
            f"In the context of **{active_concept_node}**, how does that relate to the target question variables? Let's check our steps or formulas together. If you'd like to return to the options, type 'A' or 'B'!"
        )


# ══════════════════════════════════════════════════════════════
#  WEBSOCKET CHAT ENDPOINT  —  graph-aware RAG pipeline
# ══════════════════════════════════════════════════════════════
@app.websocket("/tutor/chat")
async def websocket_tutor_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger_ws.info(f"WebSocket connected from {client_host}")
    client = genai.Client()

    try:
        while True:
            raw_data  = await websocket.receive_text()
            data_dict = json.loads(raw_data)
            payload   = ChatPayload(**data_dict)

            logger_ws.info(
                f"[{payload.session_id}] Message received — "
                f"q_id={payload.question_id or 'none'}, "
                f"history={len(payload.chat_history)} turns, "
                f"msg='{payload.student_message[:60]}...'"
            )

            # ── Step 1: Fetch learner memory ───────────────────────────────
            learner_memory = app.state.graph.get_learner_memory(payload.session_id)
            logger_ws.debug(
                f"[{payload.session_id}] Mastery topics tracked: "
                f"{len(learner_memory.get('mastery', {}))}"
            )

            # ── Step 2: Resolve question context EARLY (needed by graph + files) ──
            target_q       = None
            active_chapter = "General"
            active_subject = ""

            if payload.question_id:
                target_q = next(
                    (q for q in QUESTIONS_RAM if
                     f"q_{q.get('question_number', '')}" == payload.question_id or
                     q.get("id") == payload.question_id),
                    None
                )

            if target_q:
                active_chapter = target_q.get("chapter", "General")
                active_subject = target_q.get("subject", "")
                
            active_concept_node = None
            if payload.question_id and payload.question_id in app.state.graph.G:
                for _, tgt, d in app.state.graph.G.out_edges(payload.question_id, data=True):
                    if d.get("type") == "tests_concept":
                        active_concept_node = tgt
                        break
                        
            if not active_concept_node:
                # fallback mapping if question wasn't linked perfectly
                active_concept_node = app.state.graph._find_chapter_node(active_chapter, active_subject) or active_chapter

            if target_q:
                logger_ws.debug(
                    f"[{payload.session_id}] Question resolved: "
                    f"concept_node='{active_concept_node}', chapter='{active_chapter}'"
                )
            elif payload.question_id:
                logger_ws.warning(
                    f"[{payload.session_id}] question_id '{payload.question_id}' not found in RAM."
                )
            elif payload.chapter_context:
                parts = payload.chapter_context.split(":", 1)
                if len(parts) == 2:
                    active_subject = parts[0].strip()
                    active_chapter = parts[1].strip()
                else:
                    active_chapter = payload.chapter_context.strip()
                logger_ws.debug(
                    f"[{payload.session_id}] Context resolved from payload: "
                    f"chapter='{active_chapter}', subject='{active_subject}'"
                )

            # ── Step 3: Classify intent ────────────────────────────────────
            lane = run_intent_classifier(payload.student_message)
            await websocket.send_json({
                "type": "status", "lane": lane,
                "message": f"Routing to {lane} cluster..."
            })
            # ▶ Pipeline event: intent classification result
            await websocket.send_json({
                "type": "pipeline_step", "step": "intent_classify",
                "data": {
                    "lane":            lane,
                    "message_preview": payload.student_message[:80],
                }
            })

            # ── Step 4: Graph-aware context query (PIPELINE only) ──────────
            graph_ctx: dict = {}
            related_questions: dict = {}
            if lane == "PIPELINE":
                logger_graph.debug(
                    f"[{payload.session_id}] Querying knowledge graph for "
                    f"'{active_chapter}' ({active_subject or 'any subject'})..."
                )
                graph_ctx = app.state.graph.get_graph_rag_context(
                    session_id=payload.session_id,
                    chapter=active_chapter,
                    subject=active_subject,
                )
                logger_graph.info(
                    f"[{payload.session_id}] Graph ctx — "
                    f"concept='{graph_ctx.get('active_concept')}', "
                    f"mastery={graph_ctx.get('current_mastery', 0):.0%}, "
                    f"unmastered={[u['concept'] for u in graph_ctx.get('unmastered_prereqs', [])]}, "
                    f"tools={graph_ctx.get('hint_scaffolds', [])}"
                )
                # ▶ Pipeline event: graph query result
                await websocket.send_json({
                    "type": "pipeline_step", "step": "graph_query",
                    "data": {
                        "concept":          graph_ctx.get("active_concept"),
                        "mastery":          round(graph_ctx.get("current_mastery", 0), 2),
                        "prereq_chain":     graph_ctx.get("prereq_chain", []),
                        "unmastered_prereqs": [u["concept"] for u in graph_ctx.get("unmastered_prereqs", [])],
                        "hint_scaffolds":   graph_ctx.get("hint_scaffolds", []),
                        "scaffolding":      graph_ctx.get("graph_hint", "")[:200],
                    }
                })
                # Fetch real JEE questions for Option B quiz path
                related_questions = app.state.graph.get_questions_by_concept(
                    active_chapter, active_subject, limit_per_difficulty=1
                )

            # ── Step 5: Build enriched system instruction ──────────────────
            mastery_map    = learner_memory.get("mastery", {})
            misconceptions = learner_memory.get("misconceptions", {})

            if lane == "PIPELINE" and graph_ctx:
                unmastered_names = [u["concept"] for u in graph_ctx.get("unmastered_prereqs", [])]
                hint_tools       = graph_ctx.get("hint_scaffolds", [])
                rq       = related_questions
                easy_q   = rq["Easy"][0]["raw_text"]   if rq.get("Easy")   else "Generate an easier foundational variant"
                medium_q = rq["Medium"][0]["raw_text"] if rq.get("Medium") else "Generate a similar difficulty question"
                hard_q   = rq["Hard"][0]["raw_text"]   if rq.get("Hard")   else "Generate a harder extension question"

                system_instruction = (
                    "You are an elite, highly specialized IIT-JEE Intelligent Tutor.\n"
                    "Never reveal the direct answer immediately. Guide through progressive Socratic hints.\n\n"
                    "== GRAPH-AWARE LEARNER PROFILE ==\n"
                    f"Active Concept      : {graph_ctx['active_concept']}\n"
                    f"Current Mastery     : {graph_ctx['current_mastery']:.0%}\n"
                    f"Prerequisite Chain  : {graph_ctx.get('prereq_chain', [])}\n"
                    f"Unmastered Prereqs  : {unmastered_names}\n"
                    f"Required Math Tools : {hint_tools}\n"
                    f"Concept Misconception: {graph_ctx['misconceptions'] or 'None detected'}\n\n"
                    "== SCAFFOLDING DIRECTIVE ==\n"
                    f"{graph_ctx['graph_hint']}\n\n"
                    "== FULL MASTERY SNAPSHOT ==\n"
                    f"{json.dumps(mastery_map, indent=2)}\n\n"
                    "== ALL KNOWN MISCONCEPTIONS ==\n"
                    f"{json.dumps(misconceptions, indent=2)}\n\n"
                    "== MANDATORY RESPONSE FORMAT ==\n"
                    "You MUST structure EVERY response with exactly these two options:\n\n"
                    "**Option A - Let me break this down step by step:**\n"
                    "[Guided Socratic walkthrough. Ask the student to attempt each step.\n"
                    "Do NOT give the final answer. Build understanding progressively.\n"
                    "Address any unmastered prerequisites first if relevant.]\n\n"
                    "**Option B - Build your intuition with practice questions:**\n"
                    "[Provide 3 graded practice questions on the SAME concept:\n"
                    "  Easy   : (foundation level, tests prerequisite understanding)\n"
                    "  Medium : (same difficulty as current question)\n"
                    "  Hard   : (harder extension or multi-concept combination)\n"
                    "Use the related questions from the PRACTICE QUESTIONS section if they fit well.]\n\n"
                    "End with: Reply A to work through this problem together, or B to start with practice questions.\n\n"
                    "== RELATED PRACTICE QUESTIONS (use these for Option B) ==\n"
                    f"Easy   : {easy_q[:250]}\n"
                    f"Medium : {medium_q[:250]}\n"
                    f"Hard   : {hard_q[:250]}\n"
                )
            else:
                # DIRECT lane — lightweight, no retrieval overhead
                system_instruction = f"""You are an elite IIT-JEE Intelligent Tutor.
Be concise and direct. Check answers, confirm or correct with brief reasoning.
Student Mastery Snapshot: {json.dumps(mastery_map)}
Prior Misconceptions: {json.dumps(misconceptions)}
"""

            # ── Step 6: Attach RELEVANT reference files (PIPELINE only) ───
            contents_payload = []

            if lane == "PIPELINE":
                file_refs = getattr(app.state, "file_store_registry", {})
                relevant_files = app.state.graph.get_relevant_files_for_concept(
                    chapter=active_chapter,
                    subject=active_subject,
                    file_registry=file_refs,
                    max_files=5,
                )
                # Fall back to first 3 corpus files if no subject/chapter match
                attach_list = relevant_files if relevant_files else list(file_refs.keys())[:3]

                logger_ws.debug(
                    f"[{payload.session_id}] PIPELINE — attaching "
                    f"{len(attach_list)}/{len(file_refs)} files: {attach_list}"
                )
                # ▶ Pipeline event: file selection result
                await websocket.send_json({
                    "type": "pipeline_step", "step": "file_select",
                    "data": {
                        "selected":       attach_list,
                        "total_in_store": len(file_refs),
                    }
                })
                for file_name in attach_list:
                    cloud_id = file_refs.get(file_name)
                    if not cloud_id:
                        continue
                    mime = (
                        "application/json"
                        if file_name.lower().endswith(".json")
                        else "application/pdf"
                    )
                    contents_payload.append(
                        types.Part.from_uri(file_uri=cloud_id, mime_type=mime)
                    )

            # ── Step 7: Append last 4 chat history turns ───────────────────
            for turn in payload.chat_history[-4:]:
                role = "user" if turn.get("role") == "user" else "model"
                contents_payload.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=turn.get("content", ""))]
                    )
                )

            # ── Step 8: Inject question context into system instruction ────
            if target_q:
                system_instruction += (
                    f"\n\n══ ACTIVE QUESTION CONTEXT ══\n{json.dumps(target_q)}"
                )
                logger_ws.debug(
                    f"[{payload.session_id}] Question context injected: "
                    f"{target_q.get('chapter', 'unknown chapter')}"
                )

            # ── Step 9: Append user message ────────────────────────────────
            contents_payload.append(payload.student_message)

            # ── Step 10: Stream response from Gemini ───────────────────────
            logger_ws.info(
                f"[{payload.session_id}] Calling Gemini 2.5 Flash (lane={lane})..."
            )
            full_response_buffer = ""
            token_count = 0
            try:
                response_stream = client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    ),
                )

                for chunk in response_stream:
                    if chunk.text:
                        full_response_buffer += chunk.text
                        token_count += len(chunk.text.split())
                        await websocket.send_json({"type": "token", "text": chunk.text})
            except Exception as gemini_err:
                logger_ws.error(
                    f"[{payload.session_id}] Gemini generation failed, falling back to local Socratic simulation: {gemini_err}"
                )
                import asyncio
                fallback_text = get_local_socratic_fallback(
                    target_q, payload.student_message, active_concept_node, active_chapter, active_subject
                )
                full_response_buffer = fallback_text
                
                # Stream the fallback text in chunks
                chunk_size = 12
                for i in range(0, len(fallback_text), chunk_size):
                    chunk = fallback_text[i:i+chunk_size]
                    await websocket.send_json({"type": "token", "text": chunk})
                    await asyncio.sleep(0.01) # 10ms delay for natural stream feel
                token_count = len(fallback_text.split())

            logger_ws.info(
                f"[{payload.session_id}] Stream complete — ~{token_count} words sent."
            )
            # ▶ Pipeline event: LLM generation complete
            await websocket.send_json({
                "type": "pipeline_step", "step": "llm_complete",
                "data": {
                    "model": "gemini-2.5-flash",
                    "words": token_count,
                    "lane":  lane,
                }
            })

            # ── Step 11: Graph-aware mastery update ────────────────────────
            delta      = 0.0
            resp_lower = full_response_buffer.lower()
            msg_lower  = payload.student_message.lower()

            # Student comprehension signals
            if any(w in msg_lower for w in [
                "i get it", "i understand", "got it", "makes sense", "clear now", "i see"
            ]):
                delta += 0.15
                logger_ws.debug(f"[{payload.session_id}] Comprehension signal → Δmastery +0.15")

            elif any(w in msg_lower for w in [
                "correct", "right answer", "is it correct", "is this right"
            ]):
                delta += 0.08

            elif any(w in msg_lower for w in [
                "confused", "don't understand", "not clear", "lost", "stuck"
            ]):
                delta -= 0.08
                learner_memory["misconceptions"][active_concept_node] = (
                    "Student expressed confusion during session."
                )
                logger_ws.debug(f"[{payload.session_id}] Confusion signal → Δmastery -0.08")

            # Tutor assessment signals
            if any(w in resp_lower for w in [
                "excellent!", "correct!", "well done", "that's right", "perfect!"
            ]):
                delta += 0.08

            elif any(w in resp_lower for w in [
                "not quite", "that's incorrect", "misconception", "common mistake",
                "wrong approach"
            ]):
                delta -= 0.05
                if active_concept_node not in learner_memory["misconceptions"]:
                    learner_memory["misconceptions"][active_concept_node] = (
                        "Tutor identified an error in the student's approach."
                    )

            # Small engagement bonus for every PIPELINE (deep-work) turn
            if lane == "PIPELINE" and not msg_lower.startswith("please help me solve this question"):
                delta += 0.03

            current_mastery = learner_memory["mastery"].get(active_concept_node, 0.0)
            new_mastery     = round(min(1.0, max(0.0, current_mastery + delta)), 2)
            learner_memory["mastery"][active_concept_node] = new_mastery

            logger_ws.info(
                f"[{payload.session_id}] Mastery '{active_concept_node}': "
                f"{current_mastery:.2f} -> {new_mastery:.2f}  (+/-{delta:.2f})"
            )
            # Pipeline event: mastery update
            await websocket.send_json({
                "type": "pipeline_step", "step": "mastery_update",
                "data": {
                    "concept": active_concept_node,
                    "before":  round(current_mastery, 2),
                    "after":   new_mastery,
                    "delta":   round(delta, 2),
                }
            })

            # Reflect updated mastery on the graph node (for graph-viewer colouring)
            app.state.graph.update_concept_mastery_on_graph(
                payload.session_id, active_concept_node, new_mastery
            )

            # Persist session record (truncate AI response to avoid memory bloat)
            learner_memory["session_history"].append({
                "user":      payload.student_message,
                "ai":        full_response_buffer[:500],
                "chapter":   active_chapter,
                "lane":      lane,
                "timestamp": datetime.now().isoformat(),
            })
            app.state.graph.write_learner_memory(payload.session_id, learner_memory)
            logger_ws.debug(f"[{payload.session_id}] Learner memory persisted.")

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger_ws.info(f"WebSocket cleanly disconnected from {client_host}.")
    except Exception as e:
        logger_ws.error(f"❌ Internal error in WebSocket handler: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error. Please retry."})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["*.log", "*.json"],
        log_level="info"
    )