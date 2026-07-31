"""Tutor orchestration — intent routing, pedagogy, model gateway."""

from app.tutor.schemas import TutorIntent, TutorResponse, VerificationStatus

__all__ = ["TutorIntent", "TutorResponse", "VerificationStatus", "TutorOrchestrator"]


def __getattr__(name: str):
    if name == "TutorOrchestrator":
        from app.tutor.orchestrator import TutorOrchestrator

        return TutorOrchestrator
    raise AttributeError(name)
