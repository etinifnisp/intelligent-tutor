import os
import sys
import re
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

def log_message(log_file: Path, message: str) -> None:
    """Logs a message with a timestamp to the pipeline log."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def rule_based_classify(text: str, subject_context: str, exam_type: str, year: int) -> dict:
    """Classifies a question using rule-based keywords and context."""
    subject = None
    if subject_context:
        subject = subject_context
        
    t_lower = text.lower()
    
    # Keyword scoring fallback if no subject context is set
    if not subject:
        # Check Chemistry keywords
        chem_keywords = ["reaction", "compound", "acid", "base", "solution", "bonding", "periodic", "atom", "molecule", "mol ", "mole ", "equilibrium", "oxidation", "reduction", "kinetic", "organic", "inorganic", "isomer", "hydrocarbon", "ether", "ketone", "aldehyde", "ester", "alcohol", "hybridization", "solubility", "precipitate", "gaseous", "thermo", "entropy", "enthalpy", "chemistry", "ph ", "concentration", "valency"]
        # Check Math keywords
        math_keywords = ["matrix", "determinant", "progression", "binomial", "quadratic", "algebra", "integral", "derivative", "extrema", "limit", "continuity", "calculus", "vector", "3d ", "conic", "circle", "probability", "tangent", "parabola", "ellipse", "hyperbola", "differentiation", "equation", "angle", "triangle", "coefficient", "mathematics", "math"]
        # Check Physics keywords
        phys_keywords = ["velocity", "acceleration", "friction", "force", "mass", "torque", "inertia", "gravitation", "satellite", "orbit", "capacitor", "capacitance", "current", "resistor", "resistance", "circuit", "magnetic", "field", "induction", "lens", "mirror", "prism", "wavelength", "photon", "photoelectric", "semiconductor", "diode", "nuclear", "decay", "frequency", "wave", "interference", "diffraction", "sound", "physics", "refraction"]
        
        chem_score = sum(1.5 for kw in chem_keywords if kw in t_lower)
        math_score = sum(1.5 for kw in math_keywords if kw in t_lower)
        phys_score = sum(1.0 for kw in phys_keywords if kw in t_lower)
        
        if chem_score > 0 or math_score > 0 or phys_score > 0:
            if chem_score >= math_score and chem_score >= phys_score:
                subject = "Chemistry"
            elif math_score >= chem_score and math_score >= phys_score:
                subject = "Mathematics"
            else:
                subject = "Physics"
        else:
            # default to Physics if we can't decide
            subject = "Physics"

    # Chapter mapping
    chapter = "General"
    topic = "General Concepts"
    
    if subject == "Physics":
        if any(w in t_lower for w in ["kinematics", "velocity", "acceleration", "friction", "plane", "mass", "rotational", "gravitation", "shm", "waves"]):
            chapter = "Mechanics"
            if "friction" in t_lower or "mass" in t_lower:
                topic = "NLM & Friction"
            elif "velocity" in t_lower or "acceleration" in t_lower:
                topic = "Kinematics"
            else:
                topic = "Rotational Motion"
        elif any(w in t_lower for w in ["thermodynamics", "temperature", "heat", "ktg"]):
            chapter = "Thermal"
            topic = "Thermodynamics"
        elif any(w in t_lower for w in ["charge", "capacitor", "capacitance", "voltage", "current", "magnetic"]):
            chapter = "Electricity"
            topic = "Electrostatics & Capacitance" if "capacitor" in t_lower else "Current Electricity"
        elif any(w in t_lower for w in ["lens", "mirror", "optics", "refraction"]):
            chapter = "Optics"
            topic = "Ray Optics"
        elif any(w in t_lower for w in ["photoelectric", "nuclear", "semiconductor", "photon"]):
            chapter = "Modern"
            topic = "Photoelectric Effect"
            
    elif subject == "Chemistry":
        if any(w in t_lower for w in ["mole", "stoichiometry", "equilibrium", "kinetics", "rate", "solutions", "electrochemistry"]):
            chapter = "Physical"
            topic = "Chemical Kinetics" if "rate" in t_lower else "Solutions"
        elif any(w in t_lower for w in ["bonding", "periodic", "coordination", "complex", "ligand"]):
            chapter = "Inorganic"
            topic = "Coordination Compounds" if "coordination" in t_lower else "Chemical Bonding"
        elif any(w in t_lower for w in ["goc", "isomerism", "hydrocarbon", "reaction", "organic", "alkene", "benzene"]):
            chapter = "Organic"
            topic = "Isomerism" if "isomerism" in t_lower else "Hydrocarbons"
            
    elif subject == "Mathematics":
        if any(w in t_lower for w in ["matrix", "determinant", "progressions", "binomial", "quadratic", "algebra"]):
            chapter = "Algebra"
            topic = "Matrices & Determinants" if "matrix" in t_lower else "Progressions"
        elif any(w in t_lower for w in ["integral", "derivative", "extrema", "limit", "continuity", "calculus"]):
            chapter = "Calculus"
            topic = "Application of Derivatives" if "extrema" in t_lower else "Integration"
        elif any(w in t_lower for w in ["line", "circle", "vector", "3d", "conic"]):
            chapter = "Coordinate"
            topic = "Vectors & 3D Geometry" if "vector" in t_lower else "Circles & Conics"
        else:
            chapter = "Others"
            topic = "Probability"

    # Difficulty
    difficulty = "Easy"
    if exam_type == "JEE_ADVANCED":
        difficulty = "Hard" if "extrema" in t_lower or "capacitor" in t_lower else "Medium"
    else:
        difficulty = "Medium" if "rough" in t_lower or "geometric" in t_lower else "Easy"

    question_type = "MCQ-single"
    marks_pos = 4
    marks_neg = -1
    
    if "[MCQ-multiple]" in text or "MCQ-multiple" in text:
        question_type = "MCQ-multiple"
        marks_pos = 4
        marks_neg = -2
    elif "[Numerical]" in text or "Numerical" in text:
        question_type = "Numerical"
        marks_pos = 4
        marks_neg = 0
    elif "[Integer]" in text or "Integer" in text:
        question_type = "Integer"
        marks_pos = 4
        marks_neg = 0
    elif "Matrix-match" in text:
        question_type = "Matrix-match"
        marks_pos = 4
        marks_neg = 0
    
    return {
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "difficulty": difficulty,
        "question_type": question_type,
        "marks_positive": marks_pos,
        "marks_negative": marks_neg
    }

def process_pdf_thread_func(pdf_path: Path, year: int, exam_type: str, filename: str, result_container: dict) -> None:
    """Thread function to parse a single PDF's text page-by-page."""
    try:
        local_corpus = []
        local_counter = 0
        current_subject_context = None
        
        doc = fitz.open(str(pdf_path))
        # Start at page index 0 (the very first page of the PDF)
        for page_idx in range(0, len(doc)):
            page = doc[page_idx]
            text = page.get_text() or ""
            
            # Detect section/subject headers on this page
            for line in text.split("\n"):
                line_strip = line.strip().upper()
                if "PART" in line_strip or "SECTION" in line_strip or "SUBJECT" in line_strip:
                    if "PHYSICS" in line_strip:
                        current_subject_context = "Physics"
                    elif "CHEMISTRY" in line_strip:
                        current_subject_context = "Chemistry"
                    elif "MATHEMATICS" in line_strip or "MATH" in line_strip:
                        current_subject_context = "Mathematics"
                elif line_strip in ["PHYSICS", "CHEMISTRY", "MATHEMATICS", "MATHS"]:
                    current_subject_context = line_strip.capitalize()
                    if current_subject_context == "Maths":
                        current_subject_context = "Mathematics"
            
            questions_on_page = []
            if "Question:" in text:
                q_splits = re.split(r'(Question:)', text)
                for i in range(1, len(q_splits), 2):
                    q_header = q_splits[i]
                    q_content = q_splits[i+1] if i+1 < len(q_splits) else ""
                    questions_on_page.append(q_header + q_content)
            else:
                q_splits = re.split(r'(Q[1-9]\.|Q\.[1-9]\.|Q\.\s*[1-9]\.)', text)
                if len(q_splits) > 1:
                    for i in range(1, len(q_splits), 2):
                        q_header = q_splits[i]
                        q_content = q_splits[i+1] if i+1 < len(q_splits) else ""
                        questions_on_page.append(q_header + q_content)
                else:
                    q_splits = re.split(r'(\(\s*[i|v|x]+\s*\)|\(\s*[a-d]\s*\))', text, re.IGNORECASE)
                    if len(q_splits) > 1:
                        for i in range(1, len(q_splits), 2):
                            q_header = q_splits[i]
                            q_content = q_splits[i+1] if i+1 < len(q_splits) else ""
                            questions_on_page.append(q_header + q_content)
                    else:
                        if any(kwd in text.lower() for kwd in ["current", "charge", "matrix", "integral", "mass", "force", "option"]):
                            questions_on_page.append(text)
                            
            for q_text in questions_on_page:
                local_counter += 1
                classification = rule_based_classify(q_text, current_subject_context, exam_type, year)
                
                question_entry = {
                    "local_idx": local_counter,
                    "paper_filename": filename,
                    "year": year,
                    "exam_type": exam_type,
                    "session": "Session_1" if exam_type == "JEE_MAIN" else "N/A",
                    "shift": "Shift_1" if "Shift1" in filename else ("Shift_2" if "Shift2" in filename else "N/A"),
                    "subject": classification.get("subject", "Physics"),
                    "chapter": classification.get("chapter", "Mechanics"),
                    "topic": classification.get("topic", "General"),
                    "difficulty": classification.get("difficulty", "Medium"),
                    "question_type": classification.get("question_type", "MCQ-single"),
                    "marks_positive": classification.get("marks_positive", 4),
                    "marks_negative": classification.get("marks_negative", -1),
                    "raw_text": q_text.strip()
                }
                local_corpus.append(question_entry)
                
        result_container["success"] = True
        result_container["corpus"] = local_corpus
    except Exception as e:
        result_container["success"] = False
        result_container["error"] = str(e)

def main() -> None:
    project_root = Path(__file__).resolve().parent
    log_file = project_root / "logs" / "pipeline.log"
    output_dir = project_root / "outputs"
    papers_dir = project_root / "papers"

    log_message(log_file, "Starting Optimized Question Extraction Phase (Text Extraction Only)...")

    # Scan directories
    main_dir = papers_dir / "Mains"
    adv_dir = papers_dir / "advanced"
    
    downloaded_papers = []
    
    # JEE Main
    if main_dir.exists():
        main_files = list(main_dir.glob("*.pdf"))
        for f in main_files:
            year_match = re.search(r'(201[5-9]|202[0-5])', f.name)
            year = int(year_match.group(1)) if year_match else 2024
            downloaded_papers.append({
                "filename": f.name,
                "year": year,
                "exam_type": "JEE_MAIN",
                "subdir": "Mains"
            })
            
    # JEE Advanced
    if adv_dir.exists():
        adv_files = list(adv_dir.glob("*.pdf"))
        for f in adv_files:
            year_match = re.search(r'(201[5-9]|202[0-5])', f.name)
            year = int(year_match.group(1)) if year_match else 2024
            downloaded_papers.append({
                "filename": f.name,
                "year": year,
                "exam_type": "JEE_ADVANCED",
                "subdir": "advanced"
            })

    total_papers = len(downloaded_papers)
    log_message(log_file, f"Found {total_papers} papers to process. Beginning extraction with 60s timeout...")

    corpus = []
    global_question_counter = 0
    skipped_papers = []

    for idx, paper in enumerate(downloaded_papers):
        year = paper["year"]
        exam_type = paper["exam_type"]
        filename = paper["filename"]
        subdir = paper["subdir"]
        
        pdf_path = papers_dir / subdir / filename
        
        percent = int(((idx + 1) / total_papers) * 100)
        progress_msg = f"[Paper {idx + 1}/{total_papers}] ({percent}%) Processing: {filename}..."
        log_message(log_file, progress_msg)
        
        if not pdf_path.exists():
            log_message(log_file, f"Warning: PDF file {pdf_path} not found. Skipping.")
            skipped_papers.append((filename, "File not found"))
            continue

        # Run text extraction in a thread with a 60-second timeout
        result_container = {"success": False, "corpus": [], "error": "Timeout"}
        thread = threading.Thread(
            target=process_pdf_thread_func,
            args=(pdf_path, year, exam_type, filename, result_container)
        )
        
        start_time = time.time()
        thread.start()
        thread.join(timeout=60.0)
        elapsed = time.time() - start_time
        
        if thread.is_alive():
            log_message(log_file, f"ERROR: Timeout (60s exceeded) parsing {filename}. Skipping paper.")
            skipped_papers.append((filename, "Timeout"))
            continue
            
        if not result_container["success"]:
            log_message(log_file, f"ERROR: Failed parsing {filename}: {result_container.get('error')}")
            skipped_papers.append((filename, f"Error: {result_container.get('error')}"))
            continue
            
        # Map local question indexes to global counter
        paper_corpus = result_container["corpus"]
        for q in paper_corpus:
            global_question_counter += 1
            q["question_number"] = global_question_counter
            del q["local_idx"]
            corpus.append(q)
            
        log_message(log_file, f"Extracted {len(paper_corpus)} questions from {filename} in {elapsed:.2f}s.")

    # Sort corpus: year desc, question_number asc
    corpus.sort(key=lambda x: (-x["year"], x["question_number"]))

    # Save corpus
    corpus_path = output_dir / "jee_corpus.json"
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2)

    log_message(log_file, f"Successfully wrote {len(corpus)} classified questions to {corpus_path}")

    # Generate extraction_report.json
    total_q = len(corpus)
    by_year = {}
    by_subject = {}
    by_type = {}
    by_difficulty = {}

    for q in corpus:
        year_key = str(q["year"])
        by_year[year_key] = by_year.get(year_key, 0) + 1
        by_subject[q["subject"]] = by_subject.get(q["subject"], 0) + 1
        by_type[q["question_type"]] = by_type.get(q["question_type"], 0) + 1
        by_difficulty[q["difficulty"]] = by_difficulty.get(q["difficulty"], 0) + 1

    report = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "total_questions": total_q,
        "skipped_papers": skipped_papers,
        "breakdown_by_year": by_year,
        "breakdown_by_subject": by_subject,
        "breakdown_by_question_type": by_type,
        "breakdown_by_difficulty": by_difficulty
    }

    report_path = output_dir / "extraction_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log_message(log_file, f"Extraction report successfully written to {report_path}")
    if skipped_papers:
        log_message(log_file, f"Warning: {len(skipped_papers)} papers were skipped or failed: {skipped_papers}")

if __name__ == "__main__":
    main()
