"""Model gateway — Gemini, Ollama-compatible, mock, and resilient adapters."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from app.config import MODEL_BASE_URL, MODEL_NAME, MODEL_PROVIDER, MODEL_TIMEOUT_SECONDS

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
                yield chunk.text


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


def create_model_gateway(provider: str | None = None) -> ModelGateway:
    selected = (provider or MODEL_PROVIDER).lower()
    if selected == "mock":
        inner: ModelGateway = MockModelGateway()
    elif selected == "ollama":
        inner = OllamaModelGateway()
    elif selected == "failing":
        inner = FailingModelGateway()
    else:
        inner = GeminiModelGateway()
    return TimeoutModelGateway(inner)
