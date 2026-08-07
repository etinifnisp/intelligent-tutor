"""Model gateway — Gemini, Ollama-compatible, OpenRouter, mock, and resilient adapters."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from app.config import (
    MODEL_BASE_URL,
    MODEL_NAME,
    MODEL_PROVIDER,
    MODEL_TIMEOUT_SECONDS,
    OPENROUTER_DEFAULT_MODEL,
    get_openrouter_api_key,
    using_openrouter,
)
from app.services.model_catalog import openrouter_failover_chain

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

logger = logging.getLogger("tutor.model")


class ModelGateway(ABC):
    @abstractmethod
    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        ...


class MockModelGateway(ModelGateway):
    """Deterministic responses for tests and offline mode."""

    def __init__(self, response_text: str | None = None) -> None:
        self.response_text = response_text or (
            "**Option A - Let me break this down step by step:**\n"
            "What principle applies here? Try naming the governing law first.\n\n"
            "**Option B - Build your intuition with practice questions:**\n"
            "1. Easy: State the core definition.\n"
            "2. Medium: Apply the formula to a similar setup.\n"
            "3. Hard: Combine two concepts from this chapter.\n"
        )

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = system_instruction, contents, temperature
        chunk_size = 16
        for i in range(0, len(self.response_text), chunk_size):
            yield self.response_text[i : i + chunk_size]


class GeminiModelGateway(ModelGateway):
    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        chunk_queue: queue.Queue[object] = queue.Queue()

        def producer() -> None:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client()
                gemini_contents = []
                for item in contents:
                    role = "user" if item["role"] == "user" else "model"
                    gemini_contents.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=item["content"])])
                    )

                stream = client.models.generate_content_stream(
                    model=MODEL_NAME if MODEL_NAME.startswith("gemini") else "gemini-2.5-flash",
                    contents=gemini_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                    ),
                )
                for chunk in stream:
                    if chunk.text:
                        chunk_queue.put(chunk.text)
            except Exception as exc:
                chunk_queue.put(exc)
            finally:
                chunk_queue.put(None)

        threading.Thread(target=producer, daemon=True).start()

        while True:
            item = await asyncio.to_thread(chunk_queue.get)
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield str(item)


class OllamaModelGateway(ModelGateway):
    """OpenAI-compatible local endpoint (Ollama, llama.cpp server)."""

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        messages = [{"role": "system", "content": system_instruction}, *contents]
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        url = f"{MODEL_BASE_URL.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    import json

                    try:
                        parsed = json.loads(data)
                        delta = parsed["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


class OpenRouterModelGateway(ModelGateway):
    """OpenRouter gateway — OpenAI-compatible streaming endpoint."""

    def __init__(self, api_key: str, model_name: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name or OPENROUTER_DEFAULT_MODEL

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        import json as _json

        messages = [{"role": "system", "content": system_instruction}, *contents]
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://jee-tutor.local",
            "X-Title": "JEE Intelligent Tutor",
            "Content-Type": "application/json",
        }
        url = f"{OPENROUTER_BASE_URL}/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"OpenRouter API error {response.status_code}: {body.decode()[:200]}"
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        parsed = _json.loads(data)
                        delta = parsed["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (_json.JSONDecodeError, KeyError, IndexError):
                        continue


def _is_retryable_openrouter_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in ("429", "503", "502", "rate-limit", "rate limit", "overloaded", "temporarily")
    )


class OpenRouterFailoverGateway(ModelGateway):
    """Try allowed OpenRouter models in order when upstream providers are rate-limited."""

    def __init__(self, api_key: str, model_chain: list[str]) -> None:
        self.api_key = api_key
        self.model_chain = model_chain
        self.model_name = model_chain[0] if model_chain else OPENROUTER_DEFAULT_MODEL

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        last_error: Exception | None = None
        for model_name in self.model_chain:
            gateway = OpenRouterModelGateway(api_key=self.api_key, model_name=model_name)
            try:
                async for token in gateway.generate_stream(
                    system_instruction,
                    contents,
                    temperature=temperature,
                ):
                    self.model_name = model_name
                    yield token
                return
            except RuntimeError as exc:
                if _is_retryable_openrouter_error(exc):
                    logger.warning("OpenRouter model %s unavailable: %s", model_name, exc)
                    last_error = exc
                    continue
                raise
        raise RuntimeError(
            "All tutor models are temporarily busy. Please wait a moment and try again."
        ) from last_error


class TimeoutModelGateway(ModelGateway):
    """Wrap a gateway with per-chunk timeout; raises on expiry."""

    def __init__(self, inner: ModelGateway, timeout_s: float | None = None) -> None:
        self.inner = inner
        self.timeout_s = timeout_s if timeout_s is not None else MODEL_TIMEOUT_SECONDS

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        agen = self.inner.generate_stream(system_instruction, contents, temperature=temperature)
        while True:
            try:
                token = await asyncio.wait_for(agen.__anext__(), timeout=self.timeout_s)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError as exc:
                logger.warning("Model stream timed out after %.1fs", self.timeout_s)
                raise TimeoutError("Model generation timed out") from exc
            yield token


class FailingModelGateway(ModelGateway):
    """Always fails — for resilience tests."""

    async def generate_stream(
        self,
        system_instruction: str,
        contents: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = system_instruction, contents, temperature
        raise RuntimeError("Simulated model failure")
        yield ""  # pragma: no cover


def create_model_gateway(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
) -> ModelGateway:
    """Factory — provider/api_key/model_name can be supplied per-request."""
    resolved_key = (api_key or get_openrouter_api_key()).strip()
    resolved_model = model_name or MODEL_NAME or OPENROUTER_DEFAULT_MODEL
    selected = (provider or MODEL_PROVIDER).lower()
    if resolved_key and selected in {"openrouter", "gemini"}:
        chain = openrouter_failover_chain(resolved_model)
        inner: ModelGateway = OpenRouterFailoverGateway(api_key=resolved_key, model_chain=chain)
    elif selected == "mock":
        inner = MockModelGateway()
    elif selected == "ollama":
        inner = OllamaModelGateway()
    elif selected == "failing":
        inner = FailingModelGateway()
    elif resolved_key:
        chain = openrouter_failover_chain(resolved_model)
        inner = OpenRouterFailoverGateway(api_key=resolved_key, model_chain=chain)
    else:
        inner = GeminiModelGateway()
    return TimeoutModelGateway(inner)
