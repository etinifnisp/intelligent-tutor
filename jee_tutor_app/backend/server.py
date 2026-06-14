import os, json, asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(title="JEE Intelligent Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/images", StaticFiles(directory="static/images"), name="images")

client = genai.Client()

PIPELINE_STEPS = {"retrieval": True, "tutor": True, "memory_assessor": True}

# ---- Task 6-7: no in-memory load of 6,567 questions at boot ----
# Replace with a real DB connection (sqlite/postgres). Stub shown below.
import sqlite3
DB_PATH = "questions.db"

def get_questions_paginated(page=1, page_size=12, filters=None):
    filters = filters or {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where, params = [], []
    for key in ("subject", "chapter", "exam_type", "difficulty", "year"):
        if filters.get(key):
            where.append(f"{key} = ?")
            params.append(filters[key])
    if filters.get("topic"):
        where.append("topic = ?")
        params.append(filters["topic"])
    if filters.get("search"):
        where.append("raw_text LIKE ?")
        params.append(f"%{filters['search']}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    total = cur.execute(f"SELECT COUNT(*) FROM questions {where_clause}", params).fetchone()[0]

    offset = (page - 1) * page_size
    rows = cur.execute(
        f"SELECT * FROM questions {where_clause} LIMIT ? OFFSET ?",
        params + [page_size, offset]
    ).fetchall()
    conn.close()

    return {
        "questions": [dict(r) for r in rows],
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
        "page": page,
    }


# ---- Task 6: Redis cache (TTL 1hr) on filter-combination results ----
try:
    import redis
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
except Exception:
    redis_client = None

CACHE_TTL = 3600

def cache_key(page, page_size, filters):
    return "q:" + json.dumps({"page": page, "page_size": page_size, **(filters or {})}, sort_keys=True)

def get_questions_cached(page=1, page_size=12, filters=None):
    key = cache_key(page, page_size, filters)
    if redis_client:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    result = get_questions_paginated(page, page_size, filters)
    if redis_client:
        redis_client.setex(key, CACHE_TTL, json.dumps(result))
    return result


@app.on_event("startup")
async def warm_cache():
    """Task 6: warm top-50 most-attempted questions at boot only.
    Boot time target < 5s — no full corpus load."""
    if redis_client:
        try:
            get_questions_cached(page=1, page_size=50, filters={})
        except Exception as e:
            print(f"Cache warm skipped: {e}")


# ---- WebSocket message handling (Task 4-5) ----
class ChatRequest(BaseModel):
    question_id: str
    context_text: str
    student_message: str
    chat_history: list[dict] = []


class MemoryAssessorAgent:
    def __init__(self, graph):
        self.graph = graph

    def run(self, session_id, question_id, student_message, tutor_response):
        if self.graph is None:
            return
        learner_state = self.graph.get_learner_memory(session_id)
        mastery = learner_state.get("mastery", {})
        misconceptions = learner_state.get("misconceptions", {})

        learner_state["mastery"] = mastery
        learner_state["misconceptions"] = misconceptions
        learner_state.setdefault("session_history", []).append({
            "question_id": question_id,
            "student_message": student_message,
            "tutor_response": tutor_response,
        })
        self.graph.write_learner_memory(session_id, learner_state)


async def run_pipeline_ws(payload: ChatRequest, session_id: str, graph, websocket: WebSocket):
    """Streams tokens directly over websocket.send_text() instead of SSE."""
    retrieved_context = payload.context_text
    if PIPELINE_STEPS.get("retrieval", True):
        retrieved_context = payload.context_text  # placeholder

    full_prompt = (
        f"Context Question: {retrieved_context}\n"
        f"Student Input: {payload.student_message}"
    )
    socratic_instruction = (
        "You are a Socratic JEE Tutor. Guide the student step-by-step. "
        "Never give the solution directly. Use LaTeX formatting for equations."
    )

    collected = []
    if PIPELINE_STEPS.get("tutor", True):
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=socratic_instruction,
                temperature=0.7,
            )
        )
        for chunk in response:
            if chunk.text:
                collected.append(chunk.text)
                await websocket.send_text(json.dumps({
                    "type": "chat_token",
                    "text": chunk.text,
                }))

    await websocket.send_text(json.dumps({"type": "chat_done"}))

    if PIPELINE_STEPS.get("memory_assessor", True):
        tutor_response = "".join(collected)
        MemoryAssessorAgent(graph).run(session_id, payload.question_id, payload.student_message, tutor_response)


# ---- Task 4-5: single /ws/{session_id} route for all message types ----
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    graph = getattr(app.state, "graph", None)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "get_questions":
                result = get_questions_cached(
                    page=msg.get("page", 1),
                    page_size=msg.get("page_size", 12),
                    filters=msg.get("filters", {}),
                )
                await websocket.send_text(json.dumps({
                    "type": "questions_result",
                    "data": result,
                }))

            elif msg_type == "tutor_chat":
                payload = ChatRequest(**msg["data"])
                await run_pipeline_ws(payload, session_id, graph, websocket)

            elif msg_type == "get_graph":
                graph_data = graph.export_subgraph() if graph else {}
                await websocket.send_text(json.dumps({
                    "type": "graph_result",
                    "data": graph_data,
                }))

            elif msg_type == "get_memory":
                learner_state = graph.get_learner_memory(session_id) if graph else {}
                await websocket.send_text(json.dumps({
                    "type": "memory_result",
                    "data": learner_state,
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }))

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
