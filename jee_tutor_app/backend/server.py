import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI(title="JEE Intelligent Tutor API")

# Allow your local React app to communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()

class ChatRequest(BaseModel):
    question_id: str
    context_text: str
    student_message: str
    chat_history: list[dict] = []

@app.get("/api/questions/{question_id}")
async def get_question(question_id: str):
    # Here you will load from your existing JSON corpus matching the ID
    # For extraction demo purposes, returning structured mockup:
    return {
        "id": question_id,
        "subject": "Physics",
        "chapter": "Electrostatics",
        "latex_content": "Find the electric potential at a distance $r$ from a charge $q$: $$V = \\frac{1}{4\\pi\\varepsilon_0}\\frac{q}{r}$$",
        "image_url": f"http://localhost:8000/static/images/sample.png" 
    }

@app.post("/api/tutor/chat")
async def stream_tutor_response(payload: ChatRequest):
    socratic_instruction = (
        "You are a Socratic JEE Tutor. Guide the student step-by-step. "
        "Never give the solution directly. Use LaTeX formatting for equations."
    )
    
    # Construct total contextual prompt payload
    full_prompt = (
        f"Context Question: {payload.context_text}\n"
        f"Student Input: {payload.student_message}"
    )

    async def generate_chunks():
        # Stream the content token by token from Gemini
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
                yield chunk.text

    return StreamingResponse(generate_chunks(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)