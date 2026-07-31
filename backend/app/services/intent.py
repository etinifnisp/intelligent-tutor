import logging

from app.tutor.router import IntentRouter

logger = logging.getLogger("tutor.intent")
_router = IntentRouter()


def run_intent_classifier(student_msg: str) -> str:
    """Legacy lane classifier — maps structured intent to PIPELINE/DIRECT."""
    result = _router.classify(student_msg)
    logger.info("Intent classified → %s (intent=%s)", result.lane, result.intent.value)
    return result.lane
