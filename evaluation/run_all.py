"""Unified offline evaluation — corpus, retrieval, verification, tutor."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.config import EVAL_DIR  # noqa: E402


def _run(name: str, fn):
    started = time.perf_counter()
    try:
        result = fn()
        elapsed = round(time.perf_counter() - started, 2)
        return {"name": name, "status": "ok", "elapsed_s": elapsed, "result": result}
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 2)
        return {"name": name, "status": "error", "elapsed_s": elapsed, "error": str(exc)}


def main() -> int:
    from evaluation.corpus_eval import evaluate as corpus_eval
    from evaluation.retrieval_eval import evaluate as retrieval_eval
    from evaluation.tutor_eval import evaluate as tutor_eval
    from evaluation.verification_eval import evaluate as verification_eval

    sections = [
        _run("corpus", corpus_eval),
        _run("retrieval", lambda: retrieval_eval(recall_k=5)),
        _run("verification", verification_eval),
        _run("tutor", tutor_eval),
    ]

    checkpoints = []
    for s in sections:
        if s["status"] == "ok" and isinstance(s.get("result"), dict):
            if "checkpoint_pass" in s["result"]:
                checkpoints.append({"name": s["name"], "pass": s["result"]["checkpoint_pass"]})

    all_pass = all(c["pass"] for c in checkpoints) if checkpoints else False
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": sections,
        "checkpoints": checkpoints,
        "all_pass": all_pass,
    }
    out = EVAL_DIR / "evaluation_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nEvaluation report: {out}")
    print(f"All checkpoints pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
