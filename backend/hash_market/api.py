"""FastAPI interface for Hash."""

from __future__ import annotations

import json
import os
import uuid
from typing import Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field

from .agents.manager import Manager
from .agents.verifier import Verifier
from .agents.worker import Worker
from .ledger import Ledger
from .llm import LLMClient, NEBIUS_BASE_URL
from .models import Goal
from .participants import phase2_agents


load_dotenv()


MANAGER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
WORKER_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


app = FastAPI(
    title="Hash",
    description="Let agents hash it out.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    """Request to start a Hash run."""

    goal: str = Field(min_length=1)


def _ledger() -> Ledger:
    return Ledger("hash.db")


def _run_events(run_id: str) -> list[dict]:
    ledger = _ledger()

    try:
        return [
            event.model_dump()
            for event in ledger.events(run_id)
        ]
    finally:
        ledger.close()


def _run_summary(run_id: str) -> dict:
    """Build a structured run response from the append-only ledger."""

    events = _run_events(run_id)

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"Run not found: {run_id}",
        )

    goal_event = next(
        (
            event
            for event in events
            if event["event_type"] == "goal_created"
        ),
        None,
    )

    task_event = next(
        (
            event
            for event in events
            if event["event_type"] == "task_posted"
        ),
        None,
    )

    work_event = next(
        (
            event
            for event in events
            if event["event_type"] == "work_submitted"
        ),
        None,
    )

    verdict_event = next(
        (
            event
            for event in events
            if event["event_type"] == "verdict"
        ),
        None,
    )

    completion_event = next(
        (
            event
            for event in events
            if event["event_type"] in {
                "goal_completed",
                "goal_failed",
            }
        ),
        None,
    )

    goal = (
        goal_event["data"]
        if goal_event
        else {}
    )

    task = (
        task_event["data"]
        if task_event
        else {}
    )

    work = (
        work_event["data"]
        if work_event
        else {}
    )

    verdict = (
        verdict_event["data"]
        if verdict_event
        else {}
    )

    return {
        "run_id": run_id,
        "status": (
            "completed"
            if completion_event
            and completion_event["event_type"] == "goal_completed"
            else "failed"
            if completion_event
            and completion_event["event_type"] == "goal_failed"
            else "running"
        ),
        "goal": {
            "id": goal.get("goal_id"),
            "prompt": goal.get("prompt"),
            "budget": goal.get("budget"),
        },
        "tasks": [
            {
                "id": task.get("task_id"),
                "type": task.get("task_type"),
                "budget": task.get("budget"),
                "acceptance_criteria": task.get(
                    "acceptance_criteria",
                    [],
                ),
            }
        ] if task else [],
        "bids": [],
        "verdicts": [
            {
                "task_id": verdict.get("task_id"),
                "worker_id": verdict.get("worker_id"),
                "passed": verdict.get("passed"),
                "reason": verdict.get("reason"),
            }
        ] if verdict else [],
        "output": work.get("output"),
        "telemetry": {
            "manager": (
                task.get("telemetry")
                if task
                else None
            ),
            "worker": work.get("telemetry"),
            "verifier": verdict.get("telemetry"),
        },
        "cost_summary": {
            "task_budget": task.get("budget"),
            "worker_price": None,
            "total_tokens": (
                (task.get("telemetry") or {}).get(
                    "total_tokens",
                    0,
                )
                + (work.get("telemetry") or {}).get(
                    "total_tokens",
                    0,
                )
                + (verdict.get("telemetry") or {}).get(
                    "total_tokens",
                    0,
                )
            ),
        },
        "events": events,
    }


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


@app.post("/runs")
def create_run(request: RunRequest) -> dict:
    """Start a Manager → Worker → Verifier run."""

    run_id = str(uuid.uuid4())

    ledger = _ledger()
    llm = LLMClient()

    try:
        manager = Manager(llm, MANAGER_MODEL)
        worker = Worker(
            llm,
            worker_id="worker-001",
            model=WORKER_MODEL,
        )
        verifier = Verifier(llm, VERIFIER_MODEL)

        goal = Goal(
            id=str(uuid.uuid4()),
            prompt=request.goal,
            budget=100.0,
        )

        ledger.append(
            run_id,
            "goal_created",
            {
                "goal_id": goal.id,
                "prompt": goal.prompt,
                "budget": goal.budget,
            },
        )

        task = manager.create_task(goal)

        if manager.last_response is None:
            raise RuntimeError("Manager did not produce telemetry")

        ledger.append(
            run_id,
            "task_posted",
            {
                "task_id": task.id,
                "task_type": task.task_type.value,
                "budget": task.budget,
                "acceptance_criteria": task.acceptance_criteria,
                "telemetry": manager.last_response.telemetry(),
            },
        )

        output = worker.execute(task)

        if worker.last_response is None:
            raise RuntimeError("Worker did not produce telemetry")

        ledger.append(
            run_id,
            "work_submitted",
            {
                "task_id": task.id,
                "worker_id": worker.worker_id,
                "telemetry": worker.last_response.telemetry(),
                "output": output,
            },
        )

        verdict = verifier.verify(
            task,
            worker.worker_id,
            output,
        )

        if verifier.last_response is None:
            raise RuntimeError("Verifier did not produce telemetry")

        ledger.append(
            run_id,
            "verdict",
            {
                "task_id": verdict.task_id,
                "worker_id": verdict.worker_id,
                "passed": verdict.passed,
                "reason": verdict.reason,
                "telemetry": verifier.last_response.telemetry(),
            },
        )

        ledger.append(
            run_id,
            "goal_completed" if verdict.passed else "goal_failed",
            {"goal_id": goal.id},
        )

        return {
            "run_id": run_id,
            "passed": verdict.passed,
            "verdict": verdict.reason,
        }

    finally:
        ledger.close()


@app.get("/runs")
def list_runs() -> list[dict]:
    """List past runs with a compact summary."""

    ledger = _ledger()

    try:
        rows = ledger.connection.execute(
            """
            SELECT run_id, MIN(id) AS first_event_id
            FROM events
            GROUP BY run_id
            ORDER BY first_event_id DESC
            """
        ).fetchall()

        summaries = []

        for run_id, _first_event_id in rows:
            events = ledger.events(run_id)

            goal = next(
                (
                    event.data
                    for event in events
                    if event.event_type == "goal_created"
                ),
                {},
            )

            verdict = next(
                (
                    event.data
                    for event in events
                    if event.event_type == "verdict"
                ),
                None,
            )

            summaries.append(
                {
                    "run_id": run_id,
                    "goal": goal.get("prompt"),
                    "passed": (
                        verdict.get("passed")
                        if verdict
                        else None
                    ),
                    "event_count": len(events),
                }
            )

        return summaries

    finally:
        ledger.close()


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    """Return the structured ledger-backed run."""

    return _run_summary(run_id)


@app.get("/runs/{run_id}/events")
def stream_events(run_id: str) -> StreamingResponse:
    """Stream existing run events as Server-Sent Events."""

    events = _run_events(run_id)

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"Run not found: {run_id}",
        )

    def generate() -> Iterator[str]:
        for event in events:
            yield (
                "event: ledger\n"
                f"data: {json.dumps(event)}\n\n"
            )

        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/benchmark")
def benchmark() -> dict:
    """Return the latest benchmark results."""

    path = Path("benchmark_results.json")

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Benchmark results not found",
        )

    return json.loads(path.read_text())


@app.get("/models")
def models() -> dict:
    """Return models available from Nebius Token Factory."""

    api_key = os.environ.get("NEBIUS_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="NEBIUS_API_KEY is not configured",
        )

    client = OpenAI(
        api_key=api_key,
        base_url=NEBIUS_BASE_URL,
    )

    response = client.models.list()

    return {
        "models": [
            {
                "id": model.id,
                "object": getattr(
                    model,
                    "object",
                    "model",
                ),
            }
            for model in response.data
        ]
    }
