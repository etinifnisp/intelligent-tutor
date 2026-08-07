"""Versioned tutor prompts."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "v1.1.0"


def build_system_prompt(
    *,
    pedagogy_constraints: str,
    pedagogy_mode: str,
    hint_level: int,
    mastery_map: dict,
    misconceptions: dict,
    graph_ctx: dict | None = None,
    evidence_block: str = "",
    question_context: dict | None = None,
    related_questions: dict | None = None,
    answer_available: bool = True,
    diagram_missing: bool = False,
) -> str:
    base = (
        f"You are an elite IIT-JEE Intelligent Tutor (prompt {PROMPT_VERSION}).\n"
        f"Pedagogy mode: {pedagogy_mode}. Hint level: {hint_level}.\n\n"
        "== METHOD-FIRST TEACHING CONTRACT ==\n"
        "Teach the student how and why the current step works; do not merely tell them what to do. "
        "Use one instructional move per response and then pause for the student's attempt. "
        "For an active problem, do not provide a full worked solution, final numerical value, "
        "correct option letter, answer key, or completed final substitution. "
        "If the student asks for the full answer, briefly explain that you will help them reach it, "
        "demonstrate only the next useful step, and stop before completing the problem.\n\n"
        f"== PEDAGOGY POLICY ==\n{pedagogy_constraints}\n\n"
        f"== LEARNER MASTERY ==\n{json.dumps(mastery_map, indent=2)}\n\n"
        f"== KNOWN MISCONCEPTIONS ==\n{json.dumps(misconceptions, indent=2)}\n"
    )

    if not answer_available:
        base += (
            "\n== DATA CONSTRAINT: NO ANSWER KEY ==\n"
            "No verified answer key exists for the current question. "
            "Do NOT claim to check whether the student's answer is correct or incorrect. "
            "Do NOT state or imply you know the right answer. "
            "Instead, guide the student through the reasoning process and ask them to justify each step.\n"
        )

    if diagram_missing:
        base += (
            "\n== DATA CONSTRAINT: DIAGRAM UNAVAILABLE ==\n"
            "This question references a figure or diagram that is not available in the corpus. "
            "Do NOT describe, invent, or assume the contents of any figure. "
            "Before reasoning about the question, ask the student to describe the diagram "
            "from their textbook or exam paper in their own words.\n"
        )

    if graph_ctx:
        unmastered = [u["concept"] for u in graph_ctx.get("unmastered_prereqs", [])]
        base += (
            "\n== GRAPH-AWARE CONTEXT ==\n"
            f"Active Concept: {graph_ctx.get('active_concept')}\n"
            f"Current Mastery: {graph_ctx.get('current_mastery', 0):.0%}\n"
            f"Prerequisite Chain: {graph_ctx.get('prereq_chain', [])}\n"
            f"Unmastered Prereqs: {unmastered}\n"
            f"Scaffolding: {graph_ctx.get('graph_hint', '')}\n"
        )

    if evidence_block:
        base += f"\n{evidence_block}\n"
        base += (
            "Use ONLY the retrieved evidence above for factual claims. "
            "Cite question_id when referencing a source.\n"
        )

    if question_context:
        base += f"\n══ ACTIVE QUESTION CONTEXT ══\n{json.dumps(question_context)}\n"

    if related_questions and pedagogy_mode == "PRACTICE":
        rq = related_questions
        easy = rq["Easy"][0]["raw_text"][:250] if rq.get("Easy") else "foundation question"
        medium = rq["Medium"][0]["raw_text"][:250] if rq.get("Medium") else "standard question"
        hard = rq["Hard"][0]["raw_text"][:250] if rq.get("Hard") else "extension question"
        base += (
            "\n== RELATED PRACTICE QUESTIONS ==\n"
            f"Easy: {easy}\nMedium: {medium}\nHard: {hard}\n"
        )

    if pedagogy_mode == "HINT":
        base += (
            "\n== RESPONSE FORMAT ==\n"
            "Give exactly one scaffolded step at the current hint level. "
            "Explain how and why that step follows from the information available. "
            "End with one short question that lets the student attempt the next step. "
            "Never reveal or offer the full answer.\n"
        )
    elif pedagogy_mode == "CHECK":
        base += (
            "\n== RESPONSE FORMAT ==\n"
            "State whether the student's answer/reasoning is correct. "
            "If wrong, explain why without giving the full solution unless asked.\n"
        )

    return base


def build_chat_contents(chat_history: list[dict[str, Any]], student_message: str) -> list[dict[str, str]]:
    contents: list[dict[str, str]] = []
    for turn in chat_history[-4:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        contents.append({"role": role, "content": turn.get("content", "")})
    contents.append({"role": "user", "content": student_message})
    return contents
