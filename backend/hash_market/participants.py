"""Hash market participant registry."""

from __future__ import annotations

from .models import Agent


def phase2_agents() -> dict[str, Agent]:
    """Return the Phase 2 Nemotron worker pool."""

    return {
        "worker-nano": Agent(
            id="worker-nano",
            name="Nemotron Nano",
            model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
            skills=["code", "copy", "research"],
            strategy="cheap",
            balance=100.0,
            reputation=50.0,
        ),
        "worker-lightning": Agent(
            id="worker-lightning",
            name="Nemotron Lightning",
            model="nvidia/Nemotron-3_5-Lightning",
            skills=["code", "copy", "research"],
            strategy="balanced",
            balance=100.0,
            reputation=50.0,
        ),
        "worker-super": Agent(
            id="worker-super",
            name="Nemotron Super",
            model="nvidia/nemotron-3-super-120b-a12b",
            skills=["code", "copy", "research"],
            strategy="quality",
            balance=100.0,
            reputation=50.0,
        ),
    }
