"""Nebius Token Factory client for Hash model calls."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import OpenAI


NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@dataclass
class LLMResponse:
    """Normalized result from a model call."""

    model: str
    content: str
    reasoning: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float

    def telemetry(self) -> dict:
        """Return serializable model-call telemetry."""
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": round(self.latency_ms, 2),
        }


class LLMClient:
    """Small wrapper around the Nebius Token Factory OpenAI API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Create a Token Factory client using the configured API key."""
        key = api_key or os.environ.get("NEBIUS_API_KEY")

        if not key:
            raise RuntimeError("NEBIUS_API_KEY is not configured")

        self.client = OpenAI(
            api_key=key,
            base_url=NEBIUS_BASE_URL,
        )

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Call a Nemotron model and normalize its response."""

        started = time.perf_counter()

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )

        latency_ms = (time.perf_counter() - started) * 1000

        choice = response.choices[0]
        message = choice.message
        usage = response.usage

        return LLMResponse(
            model=response.model,
            content=(message.content or "").strip(),
            reasoning=getattr(message, "reasoning", None),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
        )
