"""FastAPI interface for Hash."""

from __future__ import annotations

from fastapi import FastAPI

from .participants import phase2_agents

app = FastAPI(
    title="Hash",
    description="Let agents hash it out.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """Return API health status."""
    return {"status": "ok"}


@app.get("/agents")
def agents() -> list[dict]:
    """Return registered Hash market agents."""
    return [
        agent.model_dump()
        for agent in phase2_agents().values()
    ]
