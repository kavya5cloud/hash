"""End-to-end Phase 1 runner for Hash."""

from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv

from .agents.manager import Manager
from .agents.verifier import Verifier
from .agents.worker import Worker
from .ledger import Ledger
from .llm import LLMClient
from .models import Goal


MANAGER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
WORKER_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def run(goal_prompt: str) -> None:
    """Run one complete Manager → Worker → Verifier flow."""

    load_dotenv()

    run_id = str(uuid.uuid4())
    ledger = Ledger("hash.db")
    llm = LLMClient()

    manager = Manager(llm, MANAGER_MODEL)
    worker = Worker(
        llm,
        worker_id="worker-001",
        model=WORKER_MODEL,
    )
    verifier = Verifier(llm, VERIFIER_MODEL)

    goal = Goal(
        id=str(uuid.uuid4()),
        prompt=goal_prompt,
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

    print("\n=== HASH MARKET ===")
    print(f"Run: {run_id}")
    print(f"Goal: {goal.prompt}\n")

    print("[MANAGER] Decomposing goal...")
    task = manager.create_task(goal)

    manager_response = manager.last_response
    if manager_response is None:
        raise RuntimeError("Manager did not produce telemetry")

    ledger.append(
        run_id,
        "task_posted",
        {
            "task_id": task.id,
            "task_type": task.task_type.value,
            "budget": task.budget,
            "acceptance_criteria": task.acceptance_criteria,
            "telemetry": manager_response.telemetry(),
        },
    )

    print(f"  Task: {task.prompt}")
    print(f"  Budget: {task.budget}")
    print(f"  Acceptance: {task.acceptance_criteria}\n")

    print("[WORKER] Executing task...")
    output = worker.execute(task)

    worker_response = worker.last_response
    if worker_response is None:
        raise RuntimeError("Worker did not produce telemetry")

    ledger.append(
        run_id,
        "work_submitted",
        {
            "task_id": task.id,
            "worker_id": worker.worker_id,
            "telemetry": worker_response.telemetry(),
            "output": output,
        },
    )

    print("  Worker output:")
    print(output)
    print()

    print("[VERIFIER] Checking work...")
    verdict = verifier.verify(
        task,
        worker.worker_id,
        output,
    )

    verifier_response = verifier.last_response
    if verifier_response is None:
        raise RuntimeError("Verifier did not produce telemetry")

    ledger.append(
        run_id,
        "verdict",
        {
            "task_id": verdict.task_id,
            "worker_id": verdict.worker_id,
            "passed": verdict.passed,
            "reason": verdict.reason,
            "telemetry": verifier_response.telemetry(),
        },
    )

    if verdict.passed:
        ledger.append(
            run_id,
            "goal_completed",
            {"goal_id": goal.id},
        )
    else:
        ledger.append(
            run_id,
            "goal_failed",
            {"goal_id": goal.id},
        )

    print("\n=== VERDICT ===")
    print(f"Passed: {verdict.passed}")
    print(f"Reason: {verdict.reason}")

    print("\n=== EVENT LOG ===")

    for event in ledger.events(run_id):
        print(f"[{event.id}] {event.event_type} {event.data}")

    ledger.close()


if __name__ == "__main__":
    prompt = os.environ.get(
        "HASH_TEST_GOAL",
        (
            "Write a Python function called reverse_string(s) "
            "that returns the input string reversed."
        ),
    )

    run(prompt)
