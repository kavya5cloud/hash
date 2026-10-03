"""Editable Token Factory pricing configuration for Hash."""

from __future__ import annotations

import json
from pathlib import Path


PRICING_PATH = Path(__file__).parent / "config" / "pricing.json"


def load_pricing() -> dict:
    """Load the editable model pricing configuration."""
    with PRICING_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_model_pricing(model: str) -> tuple[float | None, float | None]:
    """Return input/output USD rates per 1M tokens for a model."""
    config = load_pricing()
    model_config = config.get("models", {}).get(model)

    if model_config is None:
        return None, None

    return (
        model_config.get("input_per_1m_tokens"),
        model_config.get("output_per_1m_tokens"),
    )


def calculate_cost(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float | None:
    """Calculate real Token Factory cost when rates are configured."""
    input_rate, output_rate = get_model_pricing(model)

    if input_rate is None or output_rate is None:
        return None

    return round(
        (prompt_tokens / 1_000_000) * input_rate
        + (completion_tokens / 1_000_000) * output_rate,
        8,
    )
