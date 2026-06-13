import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

def log_message(log_file: Path, message: str) -> None:
    """Logs a message with a timestamp to the pipeline log."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def run_cmd(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Runs a command and returns the return code, stdout, and stderr."""
    res = subprocess.run(args, capture_output=True, text=True, cwd=cwd, encoding="utf-8")
    return res.returncode, res.stdout, res.stderr

def main() -> None:
    # Setup path context
    project_root = Path(__file__).resolve().parent
    log_dir = project_root / "logs"
    output_dir = project_root / "outputs"
    papers_dir = project_root / "papers"
    extracted_dir = project_root / "extracted"

    # Create directories
    for d in [log_dir, output_dir, papers_dir / "main", papers_dir / "advanced", extracted_dir / "images"]:
        d.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "pipeline.log"
    log_message(log_file, "Starting Setup Phase...")

    # Create venv
    venv_dir = project_root / ".venv"
    if not venv_dir.exists():
        log_message(log_file, f"Creating virtual environment at {venv_dir}...")
        ret, stdout, stderr = run_cmd([sys.executable, "-m", "venv", str(venv_dir)])
        if ret != 0:
            log_message(log_file, f"Failed to create venv: {stderr}")
            sys.exit(1)
        log_message(log_file, "Virtual environment created.")
    else:
        log_message(log_file, "Virtual environment already exists.")

    # Determine paths to python and pip inside venv
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"

    # Install packages
    packages = ["httpx", "pdfplumber", "pymupdf", "openpyxl", "google-generativeai"]
    log_message(log_file, f"Installing packages: {', '.join(packages)}...")
    ret, stdout, stderr = run_cmd([str(venv_pip), "install", "-U"] + packages)
    if ret != 0:
        log_message(log_file, f"Failed to install packages: {stderr}")
        sys.exit(1)
    
    log_message(log_file, "Packages installed successfully.")

    # Generate setup manifest
    manifest = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "python_path": str(venv_python),
        "project_root": str(project_root),
        "directories": [
            str(log_dir),
            str(output_dir),
            str(papers_dir / "main"),
            str(papers_dir / "advanced"),
            str(extracted_dir)
        ],
        "dependencies": packages
    }

    manifest_path = output_dir / "setup_complete.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log_message(log_file, f"Setup complete. Manifest written to {manifest_path}")

if __name__ == "__main__":
    main()
