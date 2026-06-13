import os
import sys
import re
import json
import time
from pathlib import Path
from datetime import datetime

# Optional Gemini API Import
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def log_message(log_file: Path, message: str) -> None:
    """Logs a message with a timestamp."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def call_gemini_solver(prompt: str, api_key: str) -> str:
    """Calls Gemini 3.5 Flash to solve the question."""
    client = genai.Client(api_key=api_key)
    
    delays = [2, 4, 8]
    for attempt, delay in enumerate(delays):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return response.text
        except Exception as e:
            if attempt == len(delays) - 1 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                raise e
            time.sleep(delay)
    return ""

def generate_html_solved_paper(paper_name: str, questions: list[dict], output_file: Path) -> None:
    """Generates a beautifully styled, self-contained HTML report with solutions."""
    # Deduce clean title from filename
    clean_title = paper_name.replace(".pdf", "").replace("_", " ")
    
    # We will build navigation links and cards
    nav_items = []
    question_cards = []
    
    for idx, q in enumerate(questions):
        q_num = idx + 1
        subject = q.get("subject", "General")
        chapter = q.get("chapter", "General")
        topic = q.get("topic", "General")
        difficulty = q.get("difficulty", "Medium")
        raw_text = q.get("raw_text", "")
        
        # Parse solution fields
        sol_data = q.get("solved_data", {})
        concept = sol_data.get("concept", "Not available")
        solution_steps = sol_data.get("solution", "Not available")
        final_answer = sol_data.get("answer", "Not available")
        mistakes = sol_data.get("mistakes", "Not available")
        
        # Difficulty badge class
        diff_class = f"badge-{difficulty.lower()}"
        # Subject badge class
        sub_class = f"badge-{subject.lower()}"
        
        # Sidebar nav item
        nav_items.append(f"""
        <a href="#question-{q_num}" class="nav-link">
            <span class="nav-q-num">Q{q_num}</span>
            <span class="nav-q-sub">{subject} - {topic}</span>
        </a>
        """)
        
        # Question card HTML
        question_cards.append(f"""
        <div id="question-{q_num}" class="question-card">
            <div class="card-header">
                <span class="q-title">Question {q_num}</span>
                <div class="badge-group">
                    <span class="badge {sub_class}">{subject}</span>
                    <span class="badge badge-chapter">{chapter}</span>
                    <span class="badge {diff_class}">{difficulty}</span>
                </div>
            </div>
            
            <div class="card-body">
                <div class="section-title">Question Text</div>
                <div class="raw-text">{raw_text}</div>
                
                <div class="section-title">Concept Tested</div>
                <div class="concept-box">
                    <span class="icon-info">💡</span> {concept}
                </div>
                
                <div class="section-title">Step-by-Step Solution</div>
                <div class="solution-steps">{solution_steps}</div>
                
                <div class="section-title">Final Answer</div>
                <div class="answer-box">
                    <span class="icon-check">✅</span> <strong>Final Answer:</strong> {final_answer}
                </div>
                
                <div class="section-title">Common Mistakes to Avoid</div>
                <div class="mistakes-box">
                    <span class="icon-warning">⚠️</span> {mistakes}
                </div>
            </div>
        </div>
        """)
        
    nav_html = "\n".join(nav_items)
    cards_html = "\n".join(question_cards)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solved: {clean_title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --bg-sidebar: #0b0f19;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            
            --primary: #3b82f6;
            --primary-hover: #60a5fa;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
            
            --physics: #3b82f6;
            --chemistry: #f97316;
            --mathematics: #10b981;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            display: flex;
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        /* Sidebar Styles */
        .sidebar {{
            width: 320px;
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            z-index: 100;
        }}
        
        .sidebar-header {{
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .sidebar-header h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            color: var(--text-main);
            margin-bottom: 4px;
        }}
        
        .sidebar-header p {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        
        .sidebar-nav {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .nav-link {{
            display: flex;
            flex-direction: column;
            padding: 12px 16px;
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-muted);
            border: 1px solid transparent;
            transition: all 0.2s ease;
        }}
        
        .nav-link:hover {{
            background-color: #1e293b;
            color: var(--text-main);
            border-color: var(--border-color);
        }}
        
        .nav-q-num {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--primary-hover);
        }}
        
        .nav-q-sub {{
            font-size: 0.75rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        /* Main Content Area */
        .main-content {{
            margin-left: 320px;
            flex: 1;
            padding: 40px;
            max-width: 1000px;
        }}
        
        .header-panel {{
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .header-panel h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.25rem;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #f8fafc 30%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .paper-meta {{
            display: flex;
            gap: 16px;
            font-size: 0.9rem;
            color: var(--text-muted);
        }}
        
        /* Question Cards */
        .question-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 40px;
            overflow: hidden;
            scroll-margin-top: 24px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .question-card:hover {{
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        
        .card-header {{
            padding: 20px 24px;
            background-color: rgba(15, 23, 42, 0.3);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}
        
        .q-title {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 1.25rem;
            color: var(--text-main);
        }}
        
        .badge-group {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .badge {{
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .badge-physics {{ background-color: rgba(59, 130, 246, 0.15); color: var(--physics); border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-chemistry {{ background-color: rgba(249, 115, 22, 0.15); color: var(--chemistry); border: 1px solid rgba(249, 115, 22, 0.3); }}
        .badge-mathematics {{ background-color: rgba(16, 185, 129, 0.15); color: var(--mathematics); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-chapter {{ background-color: rgba(148, 163, 184, 0.1); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.2); }}
        .badge-easy {{ background-color: rgba(34, 197, 94, 0.15); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.3); }}
        .badge-medium {{ background-color: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-hard {{ background-color: rgba(239, 68, 68, 0.15); color: var(--error); border: 1px solid rgba(239, 68, 68, 0.3); }}
        
        .card-body {{
            padding: 24px;
        }}
        
        .section-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 24px;
            margin-bottom: 8px;
            border-left: 3px solid var(--primary);
            padding-left: 8px;
        }}
        
        .section-title:first-of-type {{
            margin-top: 0;
        }}
        
        .raw-text {{
            background-color: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            font-size: 1rem;
            white-space: pre-wrap;
        }}
        
        .concept-box {{
            background-color: rgba(59, 130, 246, 0.08);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 0.95rem;
        }}
        
        .solution-steps {{
            padding: 4px;
            font-size: 1rem;
        }}
        
        .answer-box {{
            background-color: rgba(34, 197, 94, 0.08);
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 1.1rem;
            color: #4ade80;
        }}
        
        .mistakes-box {{
            background-color: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.2);
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 0.95rem;
        }}
        
        .icon-info, .icon-check, .icon-warning {{
            margin-right: 6px;
        }}
        
        @media (max-width: 768px) {{
            body {{
                flex-direction: column;
            }}
            .sidebar {{
                width: 100%;
                position: relative;
                height: 250px;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
            }}
            .main-content {{
                margin-left: 0;
                padding: 20px;
            }}
        }}
    </style>
    <!-- MathJax Setup -->
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true
            }},
            options: {{
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
            }}
        }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" id="MathJax-script" async></script>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>{clean_title}</h2>
            <p>Question Index</p>
        </div>
        <div class="sidebar-nav">
            {nav_html}
        </div>
    </div>
    
    <div class="main-content">
        <div class="header-panel">
            <h1>{clean_title}</h1>
            <div class="paper-meta">
                <span><strong>Total Questions:</strong> {len(questions)}</span>
                <span>•</span>
                <span><strong>Solved via:</strong> Gemini 3.5 Flash</span>
            </div>
        </div>
        
        <div class="questions-container">
            {cards_html}
        </div>
    </div>
</body>
</html>
"""
    output_file.write_text(html_content, encoding="utf-8")

def main():
    project_root = Path(__file__).resolve().parent
    log_file = project_root / "logs" / "solver.log"
    output_dir = project_root / "outputs" / "solved"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load environment variables from .env if present
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean and not line_clean.startswith("#"):
                    if "=" in line_clean:
                        k, v = line_clean.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")

    log_message(log_file, "Starting Question Paper Solver...")
    
    # Check for API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    is_mock = "--mock" in sys.argv
    if not api_key:
        log_message(log_file, "Warning: GEMINI_API_KEY not set. Using --mock mode automatically.")
        is_mock = True
        
    if not is_mock and not HAS_GENAI:
        log_message(log_file, "Error: google-genai SDK is not installed. Halting execution.")
        sys.exit(1)
        
    corpus_path = project_root / "outputs" / "jee_corpus.json"
    if not corpus_path.exists():
        log_message(log_file, f"Error: jee_corpus.json not found at {corpus_path}. Please complete extraction first.")
        sys.exit(1)
        
    # Read corpus
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    log_message(log_file, f"Loaded {len(corpus)} questions from corpus.")
    
    is_test = "--test" in sys.argv
    if is_test:
        log_message(log_file, "Running in TEST mode: limiting to 1 paper and 3 questions.")

    # Parse paper command line argument
    target_paper = None
    if "--paper" in sys.argv:
        try:
            idx = sys.argv.index("--paper")
            target_paper = sys.argv[idx + 1]
        except (ValueError, IndexError):
            log_message(log_file, "Error: --paper argument provided without paper name.")

    # Group questions by paper
    # We fallback to a paper key deduced from (year, exam_type, session, shift) if paper_filename is missing
    papers = {}
    for q in corpus:
        paper_key = q.get("paper_filename")
        if not paper_key:
            # Reconstruct fallback paper key
            year = q.get("year", 2024)
            exam = q.get("exam_type", "JEE_MAIN")
            session = q.get("session", "Session_1")
            shift = q.get("shift", "Shift_1")
            paper_key = f"{exam}_{year}_{session}_{shift}.pdf"
            
        if paper_key not in papers:
            papers[paper_key] = []
        papers[paper_key].append(q)
        
    log_message(log_file, f"Grouped questions into {len(papers)} papers.")

    if target_paper:
        if target_paper in papers:
            papers = {target_paper: papers[target_paper]}
            log_message(log_file, f"Filtered to target paper: '{target_paper}' with {len(papers[target_paper])} questions.")
        else:
            # Try to match stem or case-insensitive or partial
            matched = False
            for k in papers:
                if target_paper.lower() in k.lower():
                    papers = {k: papers[k]}
                    log_message(log_file, f"Filtered to matched paper: '{k}' with {len(papers[k])} questions.")
                    matched = True
                    break
            if not matched:
                log_message(log_file, f"Error: Paper '{target_paper}' not found in grouped papers.")
                sys.exit(1)
    
    if is_test and papers:
        first_key = list(papers.keys())[0]
        papers = {first_key: papers[first_key][:3]}
        log_message(log_file, f"Test mode filter: kept only first paper '{first_key}' with {len(papers[first_key])} questions.")
    
    # Process each paper
    solved_count = 0
    skipped_count = 0
    
    for paper_name, questions in papers.items():
        paper_stem = Path(paper_name).stem
        html_filename = f"SOLVED_{paper_stem}.html"
        html_path = output_dir / html_filename
        
        # Resume Check
        if html_path.exists():
            log_message(log_file, f"Paper {paper_name} already solved. Skipping.")
            skipped_count += 1
            continue
            
        log_message(log_file, f"Solving paper: {paper_name} ({len(questions)} questions)...")
        
        # Sort questions by question_number to ensure correct indexing
        questions.sort(key=lambda x: x.get("question_number", 0))
        
        paper_questions_solved = []
        
        for idx, q in enumerate(questions):
            q_num = idx + 1
            log_message(log_file, f"[{paper_name}] Solving Question {q_num}/{len(questions)}...")
            
            raw_text = q.get("raw_text", "")
            subject = q.get("subject", "General")
            
            prompt = f"""
Solve the following IIT-JEE {subject} question. 
Provide a clear, detailed, and mathematically rigorous solution.

Question Text:
{raw_text}

You MUST return a JSON object with EXACTLY the following keys:
- "concept": A brief, clear explanation of the core concept being tested (1-2 sentences).
- "solution": A detailed step-by-step mathematical solution. Use LaTeX formatting for all mathematical expressions. Use standard delimiters: "$" for inline equations (e.g. $x = 2$) and "$$" for block/display equations.
- "answer": The final correct answer (e.g., "Option (A)" or the exact numerical value).
- "mistakes": 1-2 common errors, misconceptions, or math traps to watch out for.

Return ONLY the raw JSON block. Do not wrap it in markdown code blocks or add any trailing text.
"""
            if is_mock:
                solved_data = {
                    "concept": "Mock concept for " + subject + " question.",
                    "solution": r"This is a mock step-by-step solution for testing LaTeX rendering: $\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$. We can also render block math: $$\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$$ and details about " + subject + " parameters.",
                    "answer": "Option (A) or 42",
                    "mistakes": "Verify alignment of LaTeX operators and check integration boundaries."
                }
                q["solved_data"] = solved_data
                paper_questions_solved.append(q)
            else:
                try:
                    response_text = call_gemini_solver(prompt, api_key)
                    
                    # Clean block code wrapping if returned
                    clean_json = response_text.strip()
                    if clean_json.startswith("```"):
                        match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                        if match:
                            clean_json = match.group(0)
                            
                    solved_data = json.loads(clean_json)
                    q["solved_data"] = solved_data
                    paper_questions_solved.append(q)
                except Exception as e:
                    log_message(log_file, f"Error solving question {q_num} of {paper_name}: {e}")
                    # Fallback empty solved_data
                    q["solved_data"] = {
                        "concept": "Error calling Gemini solver.",
                        "solution": f"Could not solve this question automatically: {e}",
                        "answer": "N/A",
                        "mistakes": "None"
                    }
                    paper_questions_solved.append(q)
                
            # Rate limiting delay (1 second between API calls)
            if not is_mock:
                time.sleep(1.0)
            
        # Generate HTML report
        try:
            generate_html_solved_paper(paper_name, paper_questions_solved, html_path)
            log_message(log_file, f"Successfully saved solved report to {html_path.name}")
            solved_count += 1
        except Exception as e:
            log_message(log_file, f"Error generating HTML report for {paper_name}: {e}")
            
    log_message(log_file, f"Solver sweep complete. Solved: {solved_count}, Skipped: {skipped_count}.")

if __name__ == "__main__":
    main()
