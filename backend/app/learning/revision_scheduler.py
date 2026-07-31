"""Revision scheduling for weak concepts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.learning.schemas import ConceptBKTState, RevisionItem

MASTERED_THRESHOLD = 0.85
WEAK_THRESHOLD = 0.45


class RevisionScheduler:
    def schedule(
        self,
        concept_id: str,
        state: ConceptBKTState,
        *,
        subject: str = "",
        is_correct: bool,
    ) -> RevisionItem | None:
        now = datetime.now(timezone.utc)
        p = state.p_known

        if state.evidence_sufficient:
            review_days = 14
            reason = "mastered_spaced_review"
        elif is_correct and p >= 0.6:
            review_days = 5
            reason = "consolidation_review"
        elif p < WEAK_THRESHOLD:
            review_days = 1
            reason = "weak_concept_priority"
        else:
            review_days = 3
            reason = "standard_review"

        next_at = now + timedelta(days=review_days)
        iso = next_at.isoformat()
        state.next_review_at = iso

        return RevisionItem(
            concept_id=concept_id,
            subject=subject,
            p_known=round(p, 4),
            next_review_at=iso,
            reason=reason,
        )

    def due_items(
        self,
        states: dict[str, ConceptBKTState],
        *,
        subject: str = "",
        concept_subjects: dict[str, str] | None = None,
    ) -> list[RevisionItem]:
        now = datetime.now(timezone.utc)
        due: list[RevisionItem] = []
        concept_subjects = concept_subjects or {}

        for cid, state in states.items():
            if subject and concept_subjects.get(cid, "") != subject:
                continue
            if not state.next_review_at:
                continue
            try:
                review_at = datetime.fromisoformat(state.next_review_at)
            except ValueError:
                continue
            if review_at <= now:
                due.append(
                    RevisionItem(
                        concept_id=cid,
                        subject=concept_subjects.get(cid, ""),
                        p_known=state.p_known,
                        next_review_at=state.next_review_at,
                        reason="due_for_review",
                    )
                )

        due.sort(key=lambda x: x.p_known)
        return due
