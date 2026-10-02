"""Reusable Phase 2 market execution service for Hash."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from .agents.verifier import Verifier
from .agents.worker import Worker
from .ledger import Ledger
from .llm import LLMClient
from .market import Market
from .models import Goal, Task
from .participants import phase2_agents


VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


@dataclass
class MarketRunResult:
    """Structured result from one Hash market run."""

    run_id: str
    goal: Goal
    task: Task
    events: list[dict]


def run_market(
    *,
    goal: Goal,
    task: Task,
    llm: LLMClient,
    ledger: Ledger,
) -> MarketRunResult:
    """Run one task through bidding, award, escrow, execution and verification."""

    run_id = str(uuid.uuid4())

    market = Market()
    agents = phase2_agents()

    workers = {
        worker_id: Worker(
            llm,
            worker_id=worker_id,
            model=agent.model,
            strategy=agent.strategy,
        )
        for worker_id, agent in agents.items()
    }

    verifier = Verifier(llm, VERIFIER_MODEL)

    ledger.append(
        run_id,
        "goal_created",
        {
            "goal_id": goal.id,
            "prompt": goal.prompt,
            "budget": goal.budget,
        },
    )

    ledger.append(
        run_id,
        "task_posted",
        {
            "task_id": task.id,
            "budget": task.budget,
            "task_type": task.task_type.value,
            "acceptance_criteria": task.acceptance_criteria,
        },
    )

    bids = []

    for worker_id, worker in workers.items():
        try:
            bid = worker.bid(task)
        except (RuntimeError, ValueError, KeyError) as exc:
            ledger.append(
                run_id,
                "bid_failed",
                {
                    "task_id": task.id,
                    "worker_id": worker_id,
                    "reason": str(exc),
                },
            )
            continue

        bids.append(bid)

        ledger.append(
            run_id,
            "sealed_bid_submitted",
            {
                "bid_id": bid.id,
                "task_id": bid.task_id,
                "worker_id": bid.worker_id,
                "price": bid.price,
                "estimated_time_seconds": (
                    bid.estimated_time_seconds
                ),
                "plan": bid.plan,
                "telemetry": (
                    worker.last_response.telemetry()
                    if worker.last_response
                    else {}
                ),
            },
        )

    if not bids:
        ledger.append(
            run_id,
            "task_unmarketable",
            {
                "task_id": task.id,
                "reason": "No worker submitted a valid bid",
            },
        )

        return MarketRunResult(
            run_id=run_id,
            goal=goal,
            task=task,
            events=[
                event.model_dump()
                for event in ledger.events(run_id)
            ],
        )

    award = market.award(task, bids, agents)

    ledger.append(
        run_id,
        "task_awarded",
        {
            "task_id": award.task_id,
            "worker_id": award.worker_id,
            "bid_id": award.bid_id,
            "price": award.price,
            "score": award.score,
            "reputation_component": (
                award.reputation_component
            ),
            "price_component": award.price_component,
        },
    )

    winning_agent = agents[award.worker_id]
    winning_worker = workers[award.worker_id]

    market.reserve_escrow(
        winning_agent,
        award.price,
    )

    ledger.append(
        run_id,
        "escrow_reserved",
        {
            "task_id": task.id,
            "worker_id": award.worker_id,
            "amount": award.price,
        },
    )

    output = winning_worker.execute(task)

    ledger.append(
        run_id,
        "work_submitted",
        {
            "task_id": task.id,
            "worker_id": award.worker_id,
            "output": output,
            "telemetry": (
                winning_worker.last_response.telemetry()
                if winning_worker.last_response
                else {}
            ),
        },
    )

    verdict = verifier.verify(
        task,
        award.worker_id,
        output,
    )

    ledger.append(
        run_id,
        "verdict",
        {
            "task_id": verdict.task_id,
            "worker_id": verdict.worker_id,
            "passed": verdict.passed,
            "reason": verdict.reason,
            "telemetry": (
                verifier.last_response.telemetry()
                if verifier.last_response
                else {}
            ),
        },
    )

    if verdict.passed:
        payment = market.settle_pass(
            winning_agent,
            award.price,
        )

        ledger.append(
            run_id,
            "payment_released",
            {
                "task_id": task.id,
                "worker_id": award.worker_id,
                "amount": payment,
            },
        )

        ledger.append(
            run_id,
            "reputation_updated",
            {
                "worker_id": award.worker_id,
                "result": "pass",
                "reputation": winning_agent.reputation,
            },
        )

        ledger.append(
            run_id,
            "goal_completed",
            {
                "goal_id": goal.id,
                "worker_id": award.worker_id,
            },
        )

    else:
        slash = market.settle_fail(
            winning_agent,
            award.price,
        )

        ledger.append(
            run_id,
            "payment_slashed",
            {
                "task_id": task.id,
                "worker_id": award.worker_id,
                "amount": slash,
            },
        )

        ledger.append(
            run_id,
            "reputation_updated",
            {
                "worker_id": award.worker_id,
                "result": "fail",
                "reputation": winning_agent.reputation,
            },
        )

        ledger.append(
            run_id,
            "task_reposted",
            {
                "task_id": task.id,
                "failed_worker_id": award.worker_id,
            },
        )

        ledger.append(
            run_id,
            "goal_failed",
            {
                "goal_id": goal.id,
                "worker_id": award.worker_id,
            },
        )

    return MarketRunResult(
        run_id=run_id,
        goal=goal,
        task=task,
        events=[
            event.model_dump()
            for event in ledger.events(run_id)
        ],
    )
