# Intelligent Tutor

An AI-powered tutoring application designed to help students learn and master concepts through an intelligent graph-based knowledge system.
The project consists of a Python FastAPI backend (monolith) and a React (Vite) frontend.

## Project Structure

```
intelligent-tutor/
├── backend/              # FastAPI monolith
│   ├── app/
│   │   ├── api/routes/   # REST + WebSocket endpoints
│   │   ├── services/     # Business logic (corpus, graph, Gemini)
│   │   ├── models/       # Pydantic schemas
│   │   ├── config.py     # Centralized paths
│   │   └── main.py       # App factory
│   ├── scripts/          # Corpus maintenance utilities
│   ├── app.py            # Entry point
│   └── requirements.txt
├── frontend/             # React + Vite SPA
└── data/
    ├── corpus/           # jee_corpus.json (6,567 questions)
    ├── papers/
    │   ├── mains/        # JEE Main PDFs
    │   └── advanced/     # JEE Advanced PDFs
    └── images/           # Extracted question images
```

## Prerequisites

- **Node.js & npm** (for the frontend)
- **Python 3.9+** (for the backend)
- **A Google API Key** (for Gemini AI capabilities)

## Local Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/etinifnisp/intelligent-tutor.git
cd intelligent-tutor
```

### 2. Backend Setup

```bash
cd backend

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

Run the backend:

```bash
python app.py
```

The backend will be available at `http://localhost:8000`.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will usually be available at `http://localhost:5173`.
