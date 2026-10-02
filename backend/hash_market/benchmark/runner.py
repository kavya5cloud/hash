"""Benchmark runner for the Hash market."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

from ..agents.verifier import Verifier
from ..agents.worker import Worker
from ..ledger import Ledger
from ..llm import LLMClient
from ..market import Market
from ..participants import phase2_agents
from .tasks import benchmark_tasks


VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def run(limit: int | None = None) -> None:
    """Run benchmark tasks through the full Hash market."""

    load_dotenv()

    tasks = benchmark_tasks()

    if limit is not None:
        tasks = tasks[:limit]

    llm = LLMClient()
    market = Market()
    ledger = Ledger("hash.db")
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

    print("\n=== HASH BENCHMARK ===")
    print(f"Tasks: {len(tasks)}")

    benchmark_id = str(uuid.uuid4())
    results = []

    for index, task in enumerate(tasks, start=1):
        run_id = str(uuid.uuid4())

        print(
            f"\n[{index}/{len(tasks)}] "
            f"{task.id} ({task.task_type.value})"
        )

        bids = []

        for worker_id, worker in workers.items():
            try:
                bid = worker.bid(task)
            except (RuntimeError, ValueError, KeyError) as exc:
                print(f"  {worker_id}: BID FAILED — {exc}")

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
                    "task_id": task.id,
                    "worker_id": worker_id,
                    "price": bid.price,
                    "estimated_time_seconds": (
                        bid.estimated_time_seconds
                    ),
                    "plan": bid.plan,
                    "telemetry": telemetry,
                },
            )

        if not bids:
            print("  NO VALID BIDS — task skipped")

            ledger.append(
                run_id,
                "task_unmarketable",
                {
                    "task_id": task.id,
                    "reason": "No worker submitted a valid bid",
                },
            )

            results.append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type.value,
                    "winner": None,
                    "price": None,
                    "passed": False,
                    "result": "NO_BIDS",
                }
            )

            continue

        award = market.award(task, bids, agents)
        winner = workers[award.worker_id]
        winning_agent = agents[award.worker_id]

        ledger.append(
            run_id,
            "task_awarded",
            {
                "benchmark_id": benchmark_id,
                "task_id": task.id,
                "worker_id": award.worker_id,
                "price": award.price,
                "score": award.score,
                "reputation_component": award.reputation_component,
                "price_component": award.price_component,
            },
        )

        market.reserve_escrow(
            winning_agent,
            award.price,
        )

        output = winner.execute(task)

        ledger.append(
            run_id,
            "work_submitted",
            {
                "benchmark_id": benchmark_id,
                "task_id": task.id,
                "worker_id": award.worker_id,
                "output": output,
                "telemetry": (
                    winner.last_response.telemetry()
                    if winner.last_response
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
                "benchmark_id": benchmark_id,
                "task_id": task.id,
                "worker_id": award.worker_id,
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

            result = "PASS"

            ledger.append(
                run_id,
                "payment_released",
                {
                    "task_id": task.id,
                    "worker_id": award.worker_id,
                    "amount": payment,
                },
            )
        else:
            slash = market.settle_fail(
                winning_agent,
                award.price,
            )

            result = "FAIL"

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
                "task_reposted",
                {
                    "task_id": task.id,
                    "failed_worker_id": award.worker_id,
                },
            )

        results.append(
            {
                "benchmark_id": benchmark_id,
                "task_id": task.id,
                "task_type": task.task_type.value,
                "winner": award.worker_id,
                "price": award.price,
                "passed": verdict.passed,
                "result": result,
            }
        )

        print(
            f"  Winner: {award.worker_id} | "
            f"Price: {award.price:.2f} | "
            f"Result: {result}"
        )

    passed = sum(result["passed"] for result in results)

    report = {
        "benchmark_id": benchmark_id,
        "completed": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }

    Path("benchmark_results.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Completed: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(results) - passed}")
    print("Report: benchmark_results.json")

    for result in results:
        print(
            f"{result['task_id']:12} "
            f"{result['task_type']:8} "
            f"{result['winner']:18} "
            f"${result['price']:.2f} "
            f"{result['result']}"
        )

    ledger.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N benchmark tasks.",
    )

    args = parser.parse_args()

    run(limit=args.limit)
