import os
import sys
import zipfile
import re
import argparse
from pathlib import Path
from datetime import datetime

def log_message(log_file: Path, message: str) -> None:
    """Logs a message with a timestamp to the console and log file."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def parse_main_filename(filepath: str) -> tuple[int, int, int]:
    """Parses year, session, and shift from JEE Main file path/filename."""
    # Find year (2015-2025)
    year_match = re.search(r'\b(201[5-9]|202[0-5])\b', filepath)
    year = int(year_match.group(1)) if year_match else 2024
    
    # Find session (Session1, Session2, etc.)
    session_match = re.search(r'Session\s*(\d)', filepath, re.IGNORECASE)
    if session_match:
        session = int(session_match.group(1))
    else:
        # Check month-based indicators if session string isn't clear
        if any(m in filepath.lower() for m in ["jan", "feb", "jun"]):
            session = 1
        elif any(m in filepath.lower() for m in ["apr", "mar", "jul"]):
            session = 2
        elif "aug" in filepath.lower():
            session = 4
        else:
            session = 1
            
    # Find shift (Shift1, Shift 2, etc.)
    shift_match = re.search(r'Shift\s*(\d)', filepath, re.IGNORECASE)
    shift = int(shift_match.group(1)) if shift_match else 1
    
    return year, session, shift

def parse_adv_filename(filepath: str) -> tuple[int, int]:
    """Parses year and paper number from JEE Advanced file path/filename."""
    # Find year (2015-2025)
    year_match = re.search(r'\b(201[5-9]|202[0-5])\b', filepath)
    year = int(year_match.group(1)) if year_match else 2024
    
    # Find paper number (Paper 1, Paper2, P1, P2)
    paper_match = re.search(r'(Paper|P)\s*(\d)', filepath, re.IGNORECASE)
    paper = int(paper_match.group(2)) if paper_match else 1
    
    return year, paper

def main() -> None:
    parser = argparse.ArgumentParser(description="Unzip JEE question papers and organize them.")
    parser.add_argument("zip_path", type=str, help="Path to the JEE_Papers.zip file")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "unzip_rename.log"
    pipeline_log = log_dir / "pipeline.log"
    
    zip_path = Path(args.zip_path).resolve()
    if not zip_path.exists():
        print(f"Error: Zip file not found at {zip_path}")
        sys.exit(1)
        
    papers_dir = project_root / "papers"
    main_dir = papers_dir / "main"
    adv_dir = papers_dir / "advanced"
    main_dir.mkdir(parents=True, exist_ok=True)
    adv_dir.mkdir(parents=True, exist_ok=True)
    
    log_message(pipeline_log, f"unzip_papers.py: Starting extraction from {zip_path}...")
    log_message(log_file, f"--- Starting Extraction from {zip_path} ---")

    count_main = 0
    count_adv = 0
    count_skipped = 0

    with zipfile.ZipFile(zip_path, "r") as z:
        for file_info in z.infolist():
            # Skip directories
            if file_info.is_dir() or not file_info.filename.endswith(".pdf"):
                continue
                
            orig_path = file_info.filename
            
            # Determine if Main or Advanced
            is_adv = any(k in orig_path.lower() for k in ["advanced", "adv"])
            is_main = any(k in orig_path.lower() for k in ["main", "mains", "session"]) and not is_adv
            
            if not is_main and not is_adv:
                # Default to Main if ambiguous, or skip. Let's default based on path
                if "mains" in orig_path.lower():
                    is_main = True
                else:
                    is_adv = True
            
            if is_main:
                year, session, shift = parse_main_filename(orig_path)
                new_filename = f"JEE_MAIN_{year}_S{session}_Shift{shift}.pdf"
                dest_path = main_dir / new_filename
                count_main += 1
            else:
                year, paper = parse_adv_filename(orig_path)
                new_filename = f"JEE_ADV_{year}_P{paper}.pdf"
                dest_path = adv_dir / new_filename
                count_adv += 1
                
            # Read pdf data and write to dest
            try:
                pdf_data = z.read(orig_path)
                # If file already exists, let's write it to avoid skipping real data
                dest_path.write_bytes(pdf_data)
                
                # Log the rename
                log_message(log_file, f"Extracted & Renamed: '{orig_path}' -> '{dest_path.name}' ({len(pdf_data) // 1024} KB)")
            except Exception as e:
                log_message(log_file, f"Error extracting '{orig_path}': {e}")
                log_message(pipeline_log, f"Error extracting '{orig_path}': {e}")
                count_skipped += 1

    report_msg = (
        f"Extraction complete.\n"
        f"- JEE Main papers extracted: {count_main} to {main_dir}\n"
        f"- JEE Advanced papers extracted: {count_adv} to {adv_dir}\n"
        f"- Files failed/skipped: {count_skipped}"
    )
    log_message(pipeline_log, f"unzip_papers.py: {report_msg}")
    log_message(log_file, report_msg)

if __name__ == "__main__":
    main()
