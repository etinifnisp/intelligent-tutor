"""Shared learner stats logic (DRY for memory routes)."""

from __future__ import annotations

from typing import Any

from fastapi import Request


def build_learner_stats(user_id: str, request: Request) -> dict[str, Any]:
    graph = request.app.state.graph
    memory = graph.get_learner_memory(user_id)
    mastery = memory.get("mastery", {})
    G = graph.G

    chapter_concepts: dict[str, list] = {}
    subject_chapters = {"Physics": [], "Chemistry": [], "Mathematics": []}

    for node, data in G.nodes(data=True):
        if data.get("type") == "chapter":
            subj = data.get("subject", "General")
            if subj in subject_chapters:
                subject_chapters[subj].append(node)
            chapter_concepts.setdefault(node, [])
        elif data.get("type") == "concept":
            parent = data.get("parent_chapter")
            if parent:
                chapter_concepts.setdefault(parent, []).append(node)

    chapter_mastery = {}
    for chapter, concepts in chapter_concepts.items():
        if not concepts:
            chapter_mastery[chapter] = mastery.get(chapter, 0.0)
        else:
            total = sum(mastery.get(c, 0.0) for c in concepts)
            chapter_mastery[chapter] = total / len(concepts)

    subject_averages = {}
    for subj, chapters in subject_chapters.items():
        if not chapters:
            subject_averages[subj] = 0.0
        else:
            total = sum(chapter_mastery[c] for c in chapters)
            subject_averages[subj] = round(total / len(chapters), 2)

    return {
        "user_id": user_id,
        "mastery": mastery,
        "misconceptions": memory.get("misconceptions", {}),
        "session_count": len(memory.get("session_history", [])),
        "subject_averages": subject_averages,
        "subject_chapters": subject_chapters,
        "chapter_mastery": chapter_mastery,
        "next_concepts": {
            "Physics": graph.get_adaptive_next_concept(user_id, "Physics"),
            "Chemistry": graph.get_adaptive_next_concept(user_id, "Chemistry"),
            "Mathematics": graph.get_adaptive_next_concept(user_id, "Mathematics"),
        },
    }
