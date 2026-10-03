"""Deterministic guardrails for Hash execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailConfig:
    """Hard execution limits enforced outside model reasoning."""

    max_rounds: int = 2
    max_retries: int = 1
    max_output_chars: int = 20_000
    max_task_budget: float = 100.0


def validate_round(round_number: int, config: GuardrailConfig | None = None) -> None:
    """Reject execution beyond the configured round limit."""
    config = config or GuardrailConfig()

    if round_number < 1:
        raise ValueError("Round number must be positive")

    if round_number > config.max_rounds:
        raise ValueError("Maximum market rounds exceeded")


def validate_retry(retry_number: int, config: GuardrailConfig | None = None) -> None:
    """Reject execution beyond the configured retry limit."""
    config = config or GuardrailConfig()

    if retry_number < 0:
        raise ValueError("Retry number cannot be negative")

    if retry_number > config.max_retries:
        raise ValueError("Maximum retries exceeded")


def validate_output(output: str, config: GuardrailConfig | None = None) -> None:
    """Reject outputs larger than the configured deterministic limit."""
    config = config or GuardrailConfig()

    if len(output) > config.max_output_chars:
        raise ValueError("Model output exceeds maximum allowed size")


def validate_budget(budget: float, config: GuardrailConfig | None = None) -> None:
    """Reject tasks whose budget exceeds the configured hard cap."""
    config = config or GuardrailConfig()

    if budget <= 0:
        raise ValueError("Task budget must be positive")

    if budget > config.max_task_budget:
        raise ValueError("Task budget exceeds maximum allowed budget")
