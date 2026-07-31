"""Text helpers for verification — no tutor imports."""

from __future__ import annotations

from typing import Optional


def response_reveals_answer(text: str, correct: Optional[str]) -> bool:
    if not correct:
        return False
    lower = text.lower()
    patterns = [
        f"answer is {correct.lower()}",
        f"correct answer is {correct.lower()}",
        f"correct answer is option {correct.lower()}",
        f"option {correct.lower()} is correct",
        f"the answer is option {correct.lower()}",
    ]
    return any(p in lower for p in patterns)
