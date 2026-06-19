import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

# Import Layer 3 Manager
from graph import KnowledgeGraphManager

app = FastAPI(title="JEE Intelligent Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory data array
QUESTIONS_RAM = []

def load_questions_into_ram():
    """Boot Sequence Phase 1: Loads all questions into system RAM."""
    global QUESTIONS_RAM
    # Look for files either inside backend/ or from root relative paths
    paths_to_check = ["jee_corpus.json", "../jee_corpus.json"]
    target_path = None
    
    for p in paths_to_check:
        if os.path.exists(p):
            target_path = p
            break

    if target_path:
        try:
            with open(target_path, "r") as f:
                QUESTIONS_RAM = json.load(f)
            print(f"📦 Successfully loaded {len(QUESTIONS_RAM)} questions directly into RAM.")
        except Exception as e:
            print(f"❌ Failure parsing corpus json file: {e}")
            QUESTIONS_RAM = []
    else:
        print("⚠️ Corpus file 'jee_corpus.json' not discovered. Setting up fallback stubs.")
        QUESTIONS_RAM = [
            {"question_number": 1, "subject": "Physics", "chapter": "Kinematics", "difficulty": "Easy", "raw_text": "Calculate velocity..."},
            {"question_number": 2, "subject": "Physics", "chapter": "Newton's Laws", "difficulty": "Medium", "raw_text": "Find net force..."}
        ]

def get_questions_filtered(page=1, page_size=12, filters=None):
    """Filters dataset arrays instantly in RAM."""
    filters = filters or {}
    filtered = QUESTIONS_RAM

    for key in ("subject", "chapter", "difficulty"):
        if filters.get(key):
            filtered = [q for q in filtered if str(q.get(key)).lower() == str(filters[key]).lower()]
            
    if filters.get("search"):
        search_term = filters["search"].lower()
        filtered = [q for q in filtered if search_term in str(q.get("raw_text", "")).lower()]

    total = len(filtered)
    offset = (page - 1) * page_size
    paginated_slice = filtered[offset : offset + page_size]

    return {
        "questions": paginated_slice,
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
        "page": page,
    }

@app.on_event("startup")
async def boot_sequence():
    """Orchestrated single-thread boot parameters."""
    print("🚀 Initiating tutor backend system boot sequence...")
    load_questions_into_ram()
    
    app.state.graph = KnowledgeGraphManager()
    if QUESTIONS_RAM:
        app.state.graph.link_questions(QUESTIONS_RAM)
        
    print("✅ System boot sequence completed successfully. Ready for incoming connections.")


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
        learner_state.setdefault("session_history", []).append({
            "question_id": question_id,
            "student_message": student_message,
            "tutor_response": tutor_response,
        })
        self.graph.write_learner_memory(session_id, learner_state)


async def classify_intent(student_message: str) -> str:
    """Evaluates student inputs using structured schemas to determine the execution path."""
    direct_keywords = {"hello", "hi", "hey", "thanks", "thank you", "cool", "ok", "bye"}
    if student_message.strip().lower() in direct_keywords:
        return "DIRECT"

    try:
        classifier_client = genai.Client()
        prompt = (
            f"Analyze the intent of this student query regarding JEE preparation:\n"
            f"\"{student_message}\"\n\n"
            f"Classify it as either:\n"
            f"- 'PIPELINE': If they want a problem solved, want a conceptual explanation, need a hint, or are beginning a new topic study.\n"
            f"- 'DIRECT': If they are asking for confirmation on a final answer choice, basic follow-up clarity about something you just stated, or standard conversation."
        )
        
        response = classifier_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "intent": {"type": "STRING", "enum": ["PIPELINE", "DIRECT"]}
                    },
                    "required": ["intent"]
                },
                temperature=0.1,
            )
        )
        result = json.loads(response.text)
        return result.get("intent", "PIPELINE")
    except Exception as e:
        print(f"⚠️ Intent classification failed ({e}). Defaulting to PIPELINE.")
        return "PIPELINE"


async def run_pipeline_ws(payload: ChatRequest, session_id: str, graph, websocket: WebSocket):
    """The deep reasoning path: handles problem solving, hints, and conceptual explanations."""
    client = genai.Client()
    full_prompt = f"Context Material: {payload.context_text}\nStudent Input: {payload.student_message}"
    socratic_instruction = "You are a Socratic JEE Tutor. Guide step-by-step. Never give the solution directly. Use LaTeX formatting for equations."

    collected = []
    try:
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
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

    await websocket.send_text(json.dumps({"type": "chat_done"}))
    
    tutor_response = "".join(collected)
    MemoryAssessorAgent(graph).run(session_id, payload.question_id, payload.student_message, tutor_response)


async def run_direct_ws(payload: ChatRequest, session_id: str, graph, websocket: WebSocket):
    """Direct Path processing line. Skips complex file search RAG lookups."""
    client = genai.Client()
    learner_state = graph.get_learner_memory(session_id) if graph else {}
    
    full_prompt = f"Learner Profile State: {json.dumps(learner_state.get('mastery', {}))}\n"
    if payload.chat_history:
        full_prompt += f"Recent Exchanges: {json.dumps(payload.chat_history[-3:])}\n"
    
    # Clean, safe assignment without inline walrus errors
    full_prompt += f"Student Input: {payload.student_message}"

    system_instruction = "You are an empathetic conversational JEE Coach. Provide fast, targeted answers. Do not offer deep mini-lectures. Keep it clear."

    try:
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
            )
        )
        for chunk in response:
            if chunk.text:
                await websocket.send_text(json.dumps({
                    "type": "chat_token",
                    "text": chunk.text,
                }))
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

    await websocket.send_text(json.dumps({"type": "chat_done"}))


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
                result = get_questions_filtered(
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
                intent = await classify_intent(payload.student_message)
                print(f"◇ Intent classified: {intent}")
                
                if intent == "PIPELINE":
                    await run_pipeline_ws(payload, session_id, graph, websocket)
                else:
                    await run_direct_ws(payload, session_id, graph, websocket)

            elif msg_type == "get_graph":
                graph_data = graph.export_subgraph() if graph else {}
                await websocket.send_text(json.dumps({"type": "graph_result", "data": graph_data}))

            elif msg_type == "get_memory":
                learner_state = graph.get_learner_memory(session_id) if graph else {}
                await websocket.send_text(json.dumps({"type": "memory_result", "data": learner_state}))

    except WebSocketDisconnect:
        print(f"🔌 Session {session_id} disconnected.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)