"""Tutor gold-set evaluation — intent routing and verification correctness."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import EVAL_DIR, GOLD_QUESTIONS_PATH  # noqa: E402
from app.tutor.answer_check import check_answer  # noqa: E402
from app.tutor.router import IntentRouter  # noqa: E402
from app.tutor.schemas import TutorIntent, VerificationStatus  # noqa: E402
from app.verification.answer_checker import get_official_answer  # noqa: E402


def _extract_option_from_gold(raw_text: str) -> str | None:
    m = re.search(r"Answer:\s*\(?([A-D])\)?", raw_text, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"Answer\s*\(?([A-D])\)?", raw_text, re.I)
    return m.group(1).upper() if m else None


def evaluate() -> dict:
    router = IntentRouter()
    total = 0
    with_key = 0
    verified = 0
    incorrect_detected = 0
    intent_hits = 0

    with open(GOLD_QUESTIONS_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            g = json.loads(line)
            total += 1
            q = {
                "question_id": g["question_id"],
                "subject": g.get("subject"),
                "chapter": g.get("chapter"),
                "raw_text": g.get("raw_text", ""),
                "correct_answer": _extract_option_from_gold(g.get("raw_text", "")),
                "question_type": "MCQ_SINGLE",
            }
            official = get_official_answer(q) or q.get("correct_answer")
            if not official:
                continue
            with_key += 1
            q["correct_answer"] = official

            intent = router.classify("Is option B correct?", has_question=True)
            if intent.intent == TutorIntent.ANSWER_CHECK:
                intent_hits += 1

            status, _, _ = check_answer(f"My answer is option {official}", q)
            if status == VerificationStatus.VERIFIED:
                verified += 1

            wrong = "A" if official != "A" else "B"
            status_wrong, _, _ = check_answer(f"option {wrong}", q)
            if status_wrong == VerificationStatus.INCORRECT:
                incorrect_detected += 1

    accuracy = verified / with_key if with_key else 0.0
    report = {
        "gold_total": total,
        "with_answer_key": with_key,
        "verified_correct": verified,
        "incorrect_detected": incorrect_detected,
        "intent_answer_check_rate": round(intent_hits / with_key, 4) if with_key else 0.0,
        "verification_accuracy": round(accuracy, 4),
        "checkpoint_pass": accuracy >= 0.85 and with_key >= 10,
    }
    out = EVAL_DIR / "tutor_eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Tutor eval: verified={verified}/{with_key} ({accuracy:.1%}) "
        f"PASS={report['checkpoint_pass']}"
    )
    print(f"Report: {out}")
    return report


if __name__ == "__main__":
    evaluate()
