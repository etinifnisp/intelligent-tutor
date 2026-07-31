"""Deterministic verification tests — no external APIs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.verification.answer_checker import get_official_answer, verify_student_answer
from app.verification.math_verifier import compare_expressions, compare_numeric, extract_numbers, verify_numeric_submission
from app.verification.chemistry_verifier import compute_molar_mass
from app.verification.response_verifier import verify_model_response
from app.verification.schemas import VerificationStatus
from app.verification.service import VerificationService


def test_mcq_correct():
    q = {"correct_answer": "B", "subject": "Physics", "question_type": "MCQ_SINGLE"}
    report = verify_student_answer("Is option B correct?", q)
    assert report.status == VerificationStatus.VERIFIED
    assert report.confidence >= 0.9
    assert any(c.tool.endswith("match_mcq_option") or c.tool.endswith("match_option") for c in report.tool_calls)


def test_mcq_incorrect():
    q = {"correct_answer": "C", "subject": "Chemistry", "question_type": "MCQ_SINGLE"}
    report = verify_student_answer("I choose option A", q)
    assert report.status == VerificationStatus.INCORRECT


def test_numeric_integer_match():
    q = {
        "correct_answer": "42",
        "subject": "Chemistry",
        "question_type": "INTEGER",
        "category": "integer",
    }
    report = verify_student_answer("My answer is 42", q)
    assert report.status == VerificationStatus.VERIFIED
    assert report.tool_calls


def test_numeric_integer_mismatch():
    q = {
        "correct_answer": "42",
        "subject": "Physics",
        "question_type": "INTEGER",
    }
    report = verify_student_answer("I got 17", q)
    assert report.status == VerificationStatus.INCORRECT


def test_compare_expressions():
    ok, msg = compare_expressions("2+2", "4")
    assert ok is True


def test_compare_numeric_tolerance():
    ok, _ = compare_numeric(41.8, 42.0, rel_tol=0.01)
    assert ok is True


def test_molar_mass_water():
    mass, call = compute_molar_mass("H2O")
    assert call.success
    assert mass is not None
    assert 18 < mass < 19


def test_tool_failure_does_not_raise():
    report = verify_student_answer("test", {"correct_answer": None})
    assert report.status in {VerificationStatus.UNVERIFIED, VerificationStatus.PENDING}


def test_response_blocks_false_positive():
    attempt = verify_student_answer("option A", {"correct_answer": "B", "question_type": "MCQ_SINGLE"})
    resp = verify_model_response(
        "Excellent! That's correct!",
        attempt,
        pedagogy_mode="CHECK",
        hint_level=0,
        official_answer="B",
        reveal_answer=False,
    )
    assert resp.status == VerificationStatus.CONFLICTING_SOURCE


def test_response_verified_when_aligned():
    attempt = verify_student_answer("option B", {"correct_answer": "B", "question_type": "MCQ_SINGLE"})
    resp = verify_model_response(
        "Yes, that's correct!",
        attempt,
        pedagogy_mode="CHECK",
        hint_level=0,
        official_answer="B",
        reveal_answer=False,
    )
    assert resp.status == VerificationStatus.VERIFIED


def test_hint_mode_leak_detected():
    resp = verify_model_response(
        "The correct answer is option B.",
        None,
        pedagogy_mode="HINT",
        hint_level=1,
        official_answer="B",
        reveal_answer=False,
    )
    assert resp.status == VerificationStatus.UNVERIFIED
    assert "hint_leak" in resp.checks_failed


def test_gold_set_numeric_tool_coverage():
    """Gold-set integer questions with answer keys are checked by tools."""
    root = Path(__file__).resolve().parents[2]
    gold_path = root / "evaluation" / "gold_questions.jsonl"
    corpus_path = root / "data" / "corpus" / "corpus_v2.jsonl"
    if not gold_path.exists() or not corpus_path.exists():
        pytest.skip("Gold/corpus files not present")

    corpus = {}
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                corpus[row["question_id"]] = row

    checked = 0
    tool_used = 0
    for line in open(gold_path, encoding="utf-8"):
        g = json.loads(line)
        if g.get("category") != "integer":
            continue
        q = corpus.get(g["question_id"], g)
        official = get_official_answer(q)
        if not official:
            continue
        checked += 1
        report = verify_student_answer(f"My answer is {official}", q)
        if report.tool_calls:
            tool_used += 1
        assert report.status in {
            VerificationStatus.VERIFIED,
            VerificationStatus.UNVERIFIED,
            VerificationStatus.TOOL_FAILURE,
            VerificationStatus.PENDING,
        }

    assert checked > 0, "Expected integer gold questions with answer keys"
    assert tool_used >= 1, "At least some integer answers should invoke verification tools"
