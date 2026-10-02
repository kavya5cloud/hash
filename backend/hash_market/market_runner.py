"""Phase 2 real multi-worker market runner."""

from __future__ import annotations

import uuid

from dotenv import load_dotenv

from .agents.verifier import Verifier
from .agents.worker import Worker
from .ledger import Ledger
from .llm import LLMClient
from .market import Market
from .models import Goal, Task, TaskType
from .participants import phase2_agents


MANAGER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def run() -> None:
    """Run a real multi-worker market through settlement."""

    load_dotenv()

    run_id = str(uuid.uuid4())
    ledger = Ledger("hash.db")
    llm = LLMClient()
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

    goal = Goal(
        id=str(uuid.uuid4()),
        prompt=(
            "Write a Python function called reverse_string(s) "
            "that returns the input string reversed."
        ),
        budget=20.0,
    )

    task = Task(
        id=str(uuid.uuid4()),
        goal_id=goal.id,
        prompt=goal.prompt,
        task_type=TaskType.CODE,
        budget=goal.budget,
        acceptance_criteria=[
            "Function name must be exactly reverse_string.",
            "It takes a single parameter s.",
            "Returns the reversed string.",
            "Works for an empty string.",
        ],
    )

    ledger.append(
        run_id,
        "task_posted",
        {
            "task_id": task.id,
            "budget": task.budget,
            "task_type": task.task_type.value,
        },
    )

    print("\n=== HASH SEALED-BID MARKET ===")
    print(f"Run: {run_id}")
    print(f"Task: {task.prompt}")
    print(f"Budget: {task.budget}\n")

    # ---------------------------------------------------------
    # 1. SEALED BIDS
    # ---------------------------------------------------------

    bids = []

    for worker_id, worker in workers.items():
        print(f"[BID] {worker.model}")

        bid = worker.bid(task)
        bids.append(bid)

        telemetry = (
            worker.last_response.telemetry()
            if worker.last_response
            else {}
        )

        ledger.append(
            run_id,
            "sealed_bid_submitted",
            {
                "bid_id": bid.id,
                "task_id": bid.task_id,
                "worker_id": bid.worker_id,
                "price": bid.price,
                "estimated_time_seconds": bid.estimated_time_seconds,
                "plan": bid.plan,
                "telemetry": telemetry,
            },
        )

        print(f"  Price: {bid.price}")
        print(f"  ETA: {bid.estimated_time_seconds}s")
        print(f"  Plan: {bid.plan}\n")

    # ---------------------------------------------------------
    # 2. DETERMINISTIC AWARD
    # ---------------------------------------------------------

    print("[MARKET] Awarding task...")

    award = market.award(task, bids, agents)

    ledger.append(
        run_id,
        "task_awarded",
        {
            "task_id": award.task_id,
            "worker_id": award.worker_id,
            "bid_id": award.bid_id,
            "score": award.score,
            "price": award.price,
            "reputation_component": award.reputation_component,
            "price_component": award.price_component,
        },
    )

    winning_agent = agents[award.worker_id]
    winning_worker = workers[award.worker_id]

    print(f"  Winner: {award.worker_id}")
    print(f"  Price: {award.price}")
    print(f"  Score: {award.score:.4f}")

    # ---------------------------------------------------------
    # 3. ESCROW
    # ---------------------------------------------------------

    print("\n[ESCROW] Reserving payment...")

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

    print(f"  Reserved: {award.price}")
    print(f"  Worker balance: {winning_agent.balance}")

    # ---------------------------------------------------------
    # 4. EXECUTION
    # ---------------------------------------------------------

    print("\n[WORKER] Executing awarded task...")

    output = winning_worker.execute(task)

    execution_telemetry = (
        winning_worker.last_response.telemetry()
        if winning_worker.last_response
        else {}
    )

    ledger.append(
        run_id,
        "work_submitted",
        {
            "task_id": task.id,
            "worker_id": award.worker_id,
            "output": output,
            "telemetry": execution_telemetry,
        },
    )

    print("  Work submitted.")

    # ---------------------------------------------------------
    # 5. INDEPENDENT VERIFICATION
    # ---------------------------------------------------------

    print("\n[VERIFIER] Checking work...")

    verdict = verifier.verify(
        task,
        award.worker_id,
        output,
    )

    verifier_telemetry = (
        verifier.last_response.telemetry()
        if verifier.last_response
        else {}
    )

    ledger.append(
        run_id,
        "verdict",
        {
            "task_id": verdict.task_id,
            "worker_id": verdict.worker_id,
            "passed": verdict.passed,
            "reason": verdict.reason,
            "telemetry": verifier_telemetry,
        },
    )

    print(f"  Passed: {verdict.passed}")
    print(f"  Reason: {verdict.reason}")

    # ---------------------------------------------------------
    # 6. SETTLEMENT
    # ---------------------------------------------------------

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

        print("\n[SETTLEMENT] PASS")
        print(f"  Payment: {payment}")
        print(f"  Reputation: {winning_agent.reputation}")

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

        print("\n[SETTLEMENT] FAIL")
        print(f"  Slashed: {slash}")
        print(f"  Reputation: {winning_agent.reputation}")
        print("  Task reposted.")

    # ---------------------------------------------------------
    # EVENT LOG
    # ---------------------------------------------------------

    print("\n=== EVENT LOG ===")

    for event in ledger.events(run_id):
        print(f"[{event.id}] {event.event_type} {event.data}")

    ledger.close()


if __name__ == "__main__":
    run()
