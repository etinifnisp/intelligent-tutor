"""Regression coverage for practice-ready previous-year questions."""

from __future__ import annotations

from app.services.questions import prepare_practice_question


def _legacy_pyq(raw_text: str) -> dict:
    return {
        "paper_filename": "JEE_Main_2025_Apr02_Shift1.pdf",
        "year": 2025,
        "exam_type": "JEE_MAIN",
        "session": "Session_1",
        "shift": "Shift_1",
        "subject": "Physics",
        "chapter": "Work Energy Power",
        "difficulty": "Medium",
        "question_type": "MCQ-single",
        "question_number": 5155,
        "raw_text": raw_text,
        "images": ["/images/JEE_Main_2025_Apr02_Shift1/img_5155_1.png"],
    }


def test_prepare_practice_question_returns_one_clean_pyq_with_four_choices():
    question = _legacy_pyq(
        "Question: The moment of inertia of a rod is alpha.\n"
        "Options:\n"
        "(a) 2 alpha\n"
        "(b) alpha / 4\n"
        "(c) 4 alpha\n"
        "(d) alpha\n"
        "Answer: (b)"
    )

    prepared = prepare_practice_question(question)

    assert prepared is not None
    assert prepared["question_id"] == "q_5155"
    assert prepared["stem_text"] == "The moment of inertia of a rod is alpha."
    assert [option["label"] for option in prepared["options"]] == ["A", "B", "C", "D"]
    assert [option["text"] for option in prepared["options"]] == [
        "2 alpha",
        "alpha / 4",
        "4 alpha",
        "alpha",
    ]
    assert prepared["correct_answer"] == "B"
    assert prepared["source"]["kind"] == "PYQ"
    assert prepared["source"]["year"] == 2025
    assert "raw_text" not in prepared


def test_prepare_practice_question_rejects_incomplete_or_empty_choices():
    incomplete = _legacy_pyq(
        "Question: Find the angle.\n"
        "Options:\n(a)\n(b) 30 degrees\n(c)\n(d) 60 degrees\n"
        "Answer: (b)"
    )

    assert prepare_practice_question(incomplete) is None

