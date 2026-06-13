import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

client = genai.Client()

# --- PIPELINE_STEPS config dict (toggle steps without touching logic) ---
PIPELINE_STEPS = {
    "retrieval": True,
    "tutor": True,
    "memory_assessor": True,
}

class ChatRequest(BaseModel):
    question_id: str
    context_text: str
    student_message: str
    chat_history: list[dict] = []


@app.get("/api/questions/{question_id}")
async def get_question(question_id: str):
    return {
        "id": question_id,
        "subject": "Physics",
        "chapter": "Electrostatics",
        "latex_content": "Find the electric potential at a distance $r$ from a charge $q$: $$V = \\frac{1}{4\\pi\\varepsilon_0}\\frac{q}{r}$$",
        "image_url": f"http://localhost:8000/static/images/sample.png"
    }


# --- Single graph open/close: MemoryAssessorAgent (merged) ---
class MemoryAssessorAgent:
    """Merged Memory Agent + Assessor Agent. One graph open/close per call.
    All reads at top, all writes at bottom — halves graph round-trips
    and removes one Gemini call per query (assessment folded into
    the same pass as memory read instead of a separate LLM call)."""

    def __init__(self, graph):
        self.graph = graph

    def run(self, session_id: str, question_id: str, student_message: str, tutor_response: str):
        # ---- ALL READS FIRST ----
        learner_state = self.graph.get_learner_memory(session_id)
        prior_misconceptions = learner_state.get("misconceptions", {})
        mastery = learner_state.get("mastery", {})

        # ---- ASSESS (no extra Gemini call — done locally / heuristically) ----
        assessment = self._assess(student_message, tutor_response, mastery, prior_misconceptions)

        # ---- ALL WRITES LAST ----
        learner_state["mastery"] = assessment["updated_mastery"]
        learner_state["misconceptions"] = assessment["updated_misconceptions"]
        learner_state.setdefault("session_history", []).append({
            "question_id": question_id,
            "student_message": student_message,
            "tutor_response": tutor_response,
        })
        self.graph.write_learner_memory(session_id, learner_state)

        return learner_state

    def _assess(self, student_message, tutor_response, mastery, misconceptions):
        # Lightweight heuristic assessment — placeholder for real logic
        updated_mastery = dict(mastery)
        updated_misconceptions = dict(misconceptions)
        return {
            "updated_mastery": updated_mastery,
            "updated_misconceptions": updated_misconceptions,
        }


# --- run_pipeline() replaces Orchestrator class ---
async def run_pipeline(payload: ChatRequest, session_id: str, graph):
    """Single async entrypoint replacing the Orchestrator class.
    Steps toggleable via PIPELINE_STEPS without touching internal logic."""

    retrieved_context = payload.context_text
    if PIPELINE_STEPS.get("retrieval", True):
        # graph-aware context fetch / file search RAG would go here
        retrieved_context = payload.context_text  # placeholder passthrough

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
                yield chunk.text

    if PIPELINE_STEPS.get("memory_assessor", True) and graph is not None:
        tutor_response = "".join(collected)
        agent = MemoryAssessorAgent(graph)
        agent.run(session_id, payload.question_id, payload.student_message, tutor_response)


@app.post("/api/tutor/chat")
async def stream_tutor_response(payload: ChatRequest):
    graph = getattr(app.state, "graph", None)
    session_id = "default-session"  # replace with real session handling

    return StreamingResponse(
        run_pipeline(payload, session_id, graph),
        media_type="text/plain"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
