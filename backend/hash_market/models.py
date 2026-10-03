"""Core Pydantic models used by the Hash market."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Supported Hash task categories."""

    CODE = "code"
    COPY = "copy"
    RESEARCH = "research"


class Goal(BaseModel):
    """A user goal that Hash decomposes into tasks."""

    id: str
    prompt: str
    budget: float = Field(gt=0)


class Task(BaseModel):
    """A single unit of work inside a goal."""

    id: str
    goal_id: str
    prompt: str
    task_type: TaskType
    budget: float = Field(gt=0)
    acceptance_criteria: list[str] = Field(default_factory=list)


class Agent(BaseModel):
    """A model-backed participant in the market."""

    id: str
    name: str
    model: str
    skills: list[str] = Field(default_factory=list)
    strategy: str
    balance: float = 0.0
    reputation: float = Field(default=50.0, ge=0, le=100)


class Bid(BaseModel):
    """A sealed worker bid for a task."""

    id: str
    task_id: str
    worker_id: str
    price: float = Field(gt=0)
    estimated_time_seconds: float = Field(gt=0)
    plan: str


class Award(BaseModel):
    """The deterministic result of awarding a task."""

    task_id: str
    worker_id: str
    bid_id: str
    score: float
    reputation_component: float
    price_component: float
    price: float


class Verdict(BaseModel):
    """Verifier result for submitted work."""

    task_id: str
    worker_id: str
    passed: bool
    reason: str
    output: str


class LedgerEvent(BaseModel):
    """An immutable event recorded by the Hash ledger."""

    id: int | None = None
    run_id: str
    event_type: str
    timestamp: float
    data: dict = Field(default_factory=dict)
