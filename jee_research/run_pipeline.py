import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def log_message(log_file: Path, message: str) -> None:
    """Logs a message with a timestamp to the pipeline log."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def run_phase(python_exe: str, script_name: str, args: list[str], log_file: Path, project_root: Path) -> bool:
    """Runs a pipeline phase script and handles execution results."""
    script_path = project_root / script_name
    log_message(log_file, f"--- Starting Phase: {script_name} ---")
    
    cmd = [python_exe, str(script_path)] + args
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, encoding="utf-8")
    
    if res.returncode != 0:
        log_message(log_file, f"Error: Phase {script_name} failed with exit code {res.returncode}")
        log_message(log_file, f"Stderr:\n{res.stderr}")
        log_message(log_file, f"Stdout:\n{res.stdout}")
        return False
        
    log_message(log_file, f"Phase {script_name} completed successfully.")
    if res.stdout.strip():
        # log stdout lines
        for line in res.stdout.strip().split("\n"):
            log_message(log_file, f"[{script_name}] {line}")
    return True

def main() -> None:
    project_root = Path(__file__).resolve().parent
    log_file = project_root / "logs" / "pipeline.log"
    
    log_message(log_file, "=== JEE RESEARCH PIPELINE EXECUTION START ===")
    
    # Locate virtual environment python
    venv_dir = project_root / ".venv"
    if os.name == "nt":
        python_exe = str(venv_dir / "Scripts" / "python.exe")
    else:
        python_exe = str(venv_dir / "bin" / "python")
        
    if not Path(python_exe).exists():
        log_message(log_file, f"Error: Virtual environment python not found at {python_exe}. Please run setup_pipeline.py first.")
        sys.exit(1)
        
    # Phase 1: Setup (re-verify / update dependencies if needed)
    # Already done, but running it guarantees venv is intact
    if not run_phase(sys.executable, "setup_pipeline.py", [], log_file, project_root):
        log_message(log_file, "Pipeline execution aborted due to Setup failure.")
        sys.exit(1)
        
    # Phase 2: Download Papers (Runs with sample/synthetic mode by default)
    if not run_phase(python_exe, "download_papers.py", ["--sample", "--dir", "./papers"], log_file, project_root):
        log_message(log_file, "Pipeline execution aborted due to Download failure.")
        sys.exit(1)
        
    # Phase 3: Question Extraction and Classification
    if not run_phase(python_exe, "extract_questions.py", [], log_file, project_root):
        log_message(log_file, "Pipeline execution aborted due to Extraction failure.")
        sys.exit(1)
        
    # Phase 4: Topic Deep Research
    if not run_phase(python_exe, "deep_research.py", [], log_file, project_root):
        log_message(log_file, "Pipeline execution aborted due to Research failure.")
        sys.exit(1)
        
    # Phase 5: Report Generation
    if not run_phase(python_exe, "generate_report.py", [], log_file, project_root):
        log_message(log_file, "Pipeline execution aborted due to Report failure.")
        sys.exit(1)
        
    log_message(log_file, "=== JEE RESEARCH PIPELINE EXECUTION SUCCESSFUL ===")
    
if __name__ == "__main__":
    main()
