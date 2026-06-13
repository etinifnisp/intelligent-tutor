# Intelligent JEE Tutor Web App

A high-fidelity, build-less React single-page application built on top of a Flask backend, designed to help students browse past JEE questions and study with an interactive AI Tutor (powered by the Antigravity `agy.exe` CLI).

## Features
1. **Interactive Question Browser:** Filter 6,567 questions by Subject, Chapter, Topic, Year, Exam Type, and Difficulty.
2. **Beautiful LaTeX Math Formatting:** Direct mathematical formula rendering via KaTeX.
3. **AI Tutor Chat Panel:** Dedicated chatbot helper per question that streams explanations token by token.
4. **Sleek Premium UI:** Dark-mode-first aesthetic with smooth animations, badges, and a fully responsive layout.

---

## How to Run

1. **Activate the Virtual Environment:**
   Run the following command in your terminal:
   ```powershell
   & "C:\Users\91956\intelligent_tutor\jee_research\.venv\Scripts\Activate.ps1"
   ```

2. **Start the Flask Backend Server:**
   Navigate to the app folder and run the server script:
   ```powershell
   python backend/server.py
   ```
   *The server will load the question corpus and host the app at `http://127.0.0.1:5000`.*

3. **Open in Browser:**
   Go to **[http://127.0.0.1:5000](http://127.0.0.1:5000)** to launch the Intelligent JEE Tutor interface!
