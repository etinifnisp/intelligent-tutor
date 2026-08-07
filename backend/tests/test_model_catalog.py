"""Tests for OpenRouter model allowlist."""

from app.services.model_catalog import resolve_openrouter_model


def test_resolve_openrouter_model_accepts_allowed_model():
    assert resolve_openrouter_model("openai/gpt-4o-mini") == "openai/gpt-4o-mini"


def test_resolve_openrouter_model_rejects_unknown_model():
    assert resolve_openrouter_model("anthropic/claude-opus-4") == "google/gemini-3.5-flash-lite"


def test_openrouter_failover_chain_prefers_requested_then_cheap_models():
    from app.services.model_catalog import openrouter_failover_chain

    chain = openrouter_failover_chain("google/gemma-4-31b-it:free")
    assert chain[0] == "google/gemma-4-31b-it:free"
    assert "google/gemini-3.5-flash-lite" in chain
    assert "openai/gpt-4o-mini" in chain

