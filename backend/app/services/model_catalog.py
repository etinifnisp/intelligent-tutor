"""Allowed OpenRouter models for student-facing tutor requests."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import MODEL_NAME, OPENROUTER_DEFAULT_MODEL


@dataclass(frozen=True)
class TutorModelOption:
    id: str
    label: str
    provider: str
    tier: str  # free | cheap


ALLOWED_OPENROUTER_MODELS: tuple[TutorModelOption, ...] = (
    TutorModelOption("openai/gpt-4o-mini", "GPT-4o Mini", "OpenAI", "cheap"),
    TutorModelOption("google/gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite", "Google", "cheap"),
    TutorModelOption("google/gemma-4-31b-it:free", "Gemma 4 31B IT", "Google", "free"),
    TutorModelOption(
        "nvidia/nemotron-3-super-120b-a12b:free",
        "Nemotron 3 Super 120B",
        "NVIDIA",
        "free",
    ),
    TutorModelOption("qwen/qwen3.7-flash", "Qwen 3.7 Flash", "Qwen", "cheap"),
)

_ALLOWED_IDS = {model.id for model in ALLOWED_OPENROUTER_MODELS}


def list_allowed_models() -> list[dict[str, str]]:
    return [
        {
            "id": model.id,
            "label": model.label,
            "provider": model.provider,
            "tier": model.tier,
        }
        for model in ALLOWED_OPENROUTER_MODELS
    ]


def resolve_openrouter_model(requested: str | None) -> str:
    """Return a validated model id, falling back to server default."""
    candidate = (requested or MODEL_NAME or OPENROUTER_DEFAULT_MODEL).strip()
    if candidate in _ALLOWED_IDS:
        return candidate
    if OPENROUTER_DEFAULT_MODEL in _ALLOWED_IDS:
        return OPENROUTER_DEFAULT_MODEL
    return ALLOWED_OPENROUTER_MODELS[0].id


def openrouter_failover_chain(requested: str | None) -> list[str]:
    """Build an ordered model chain: user choice first, then cheap/reliable fallbacks."""
    primary = resolve_openrouter_model(requested)
    priority = [
        "google/gemini-3.5-flash-lite",
        "openai/gpt-4o-mini",
        "qwen/qwen3.7-flash",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
    ]
    chain: list[str] = []
    for model_id in (primary, *priority):
        if model_id in _ALLOWED_IDS and model_id not in chain:
            chain.append(model_id)
    return chain


def is_allowed_openrouter_model(model_id: str | None) -> bool:
    return bool(model_id and model_id in _ALLOWED_IDS)

