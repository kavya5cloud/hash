"""FastAPI interface for Hash."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
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

    def event_data(event_type: str) -> list[dict]:
        return [
            event["data"]
            for event in events
            if event["event_type"] == event_type
        ]

    goal_events = event_data("goal_created")
    task_events = event_data("task_posted")
    bid_events = event_data("sealed_bid_submitted")
    failed_bid_events = event_data("bid_failed")
    award_events = event_data("task_awarded")
    escrow_events = event_data("escrow_reserved")
    work_events = event_data("work_submitted")
    verdict_events = event_data("verdict")
    payment_events = event_data("payment_released")
    slash_events = event_data("payment_slashed")
    reputation_events = event_data("reputation_updated")
    completion_events = [
        event
        for event in events
        if event["event_type"] in {
            "goal_completed",
            "goal_failed",
        }
    ]

    goal = goal_events[0] if goal_events else {}
    task = task_events[0] if task_events else {}
    award = award_events[0] if award_events else {}
    escrow = escrow_events[0] if escrow_events else {}
    work = work_events[0] if work_events else {}
    verdict = verdict_events[0] if verdict_events else {}
    payment = payment_events[0] if payment_events else {}
    slash = slash_events[0] if slash_events else {}
    reputation = (
        reputation_events[-1]
        if reputation_events
        else {}
    )

    manager_telemetry = (
        task.get("telemetry")
        if task.get("telemetry")
        else None
    )

    worker_telemetry = work.get("telemetry")
    verifier_telemetry = verdict.get("telemetry")

    total_tokens = sum(
        telemetry.get("total_tokens", 0)
        for telemetry in (
            manager_telemetry,
            *[
                bid.get("telemetry", {})
                for bid in bid_events
            ],
            worker_telemetry,
            verifier_telemetry,
        )
        if telemetry
    )

    bids = [
        {
            "bid_id": bid.get("bid_id"),
            "worker_id": bid.get("worker_id"),
            "price": bid.get("price"),
            "estimated_time_seconds": bid.get(
                "estimated_time_seconds"
            ),
            "plan": bid.get("plan"),
            "status": (
                "awarded"
                if bid.get("bid_id") == award.get("bid_id")
                else "submitted"
            ),
            "telemetry": bid.get("telemetry"),
        }
        for bid in bid_events
    ]

    bids.extend(
        {
            "bid_id": None,
            "worker_id": failed.get("worker_id"),
            "price": None,
            "estimated_time_seconds": None,
            "plan": None,
            "status": "rejected",
            "reason": failed.get("reason"),
        }
        for failed in failed_bid_events
    )

    return {
        "run_id": run_id,
        "status": (
            "completed"
            if completion_events
            and completion_events[-1]["event_type"]
            == "goal_completed"
            else "failed"
            if completion_events
            and completion_events[-1]["event_type"]
            == "goal_failed"
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
        "bids": bids,
        "award": (
            {
                "task_id": award.get("task_id"),
                "worker_id": award.get("worker_id"),
                "bid_id": award.get("bid_id"),
                "price": award.get("price"),
                "score": award.get("score"),
                "reputation_component": award.get(
                    "reputation_component"
                ),
                "price_component": award.get(
                    "price_component"
                ),
            }
            if award
            else None
        ),
        "escrow": (
            {
                "worker_id": escrow.get("worker_id"),
                "amount": escrow.get("amount"),
            }
            if escrow
            else None
        ),
        "verdicts": [
            {
                "task_id": verdict.get("task_id"),
                "worker_id": verdict.get("worker_id"),
                "passed": verdict.get("passed"),
                "reason": verdict.get("reason"),
            }
        ] if verdict else [],
        "output": work.get("output"),
        "settlement": (
            {
                "type": "payment_released",
                "worker_id": payment.get("worker_id"),
                "amount": payment.get("amount"),
            }
            if payment
            else {
                "type": "payment_slashed",
                "worker_id": slash.get("worker_id"),
                "amount": slash.get("amount"),
            }
            if slash
            else None
        ),
        "reputation": reputation,
        "telemetry": {
            "manager": manager_telemetry,
            "bids": [
                bid.get("telemetry")
                for bid in bid_events
                if bid.get("telemetry")
            ],
            "worker": worker_telemetry,
            "verifier": verifier_telemetry,
        },
        "cost_summary": {
            "task_budget": task.get("budget"),
            "worker_price": award.get("price"),
            "total_tokens": total_tokens,
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
    """Start a full Hash market run."""

    llm = LLMClient()

    manager = Manager(llm, MANAGER_MODEL)

    goal = Goal(
        id=str(uuid.uuid4()),
        prompt=request.goal,
        budget=100.0,
    )

    task = manager.create_task(goal)

    from .market_service import run_market

    ledger = _ledger()

    try:
        result = run_market(
            goal=goal,
            task=task,
            llm=llm,
            ledger=ledger,
        )

        events = result.events

        verdict_event = next(
            (
                event
                for event in events
                if event["event_type"] == "verdict"
            ),
            None,
        )

        verdict = (
            verdict_event["data"]
            if verdict_event
            else {}
        )

        return {
            "run_id": result.run_id,
            "passed": verdict.get("passed"),
            "verdict": verdict.get("reason"),
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
