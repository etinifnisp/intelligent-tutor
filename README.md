# Intelligent Tutor

An AI-powered tutoring application designed to help students learn and master concepts through an intelligent graph-based knowledge system. 
The project consists of a Python FastAPI backend and a React (Vite) frontend.

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
The backend runs on FastAPI and uses a `.env` file for API key configuration.

```bash
cd jee_tutor_app/backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `jee_tutor_app/backend/` directory and add your Google API key:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

Run the backend server:
```bash
python server.py
```
The backend will be available at `http://localhost:8000`.

### 3. Frontend Setup
The frontend is built with React and Vite.

```bash
# Open a new terminal and navigate to the frontend directory
cd jee_tutor_app/frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```
The frontend will usually be available at `http://localhost:5173`. Open this URL in your browser to interact with the Intelligent Tutor!
