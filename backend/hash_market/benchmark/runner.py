"""Benchmark runner for the Hash market."""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from ..agents.verifier import Verifier
from ..agents.worker import Worker
from ..ledger import Ledger
from ..llm import LLMClient
from ..market import Market
from ..participants import phase2_agents
from .hidden_tests import run_hidden_tests
from .tasks import benchmark_tasks


MONOLITH_MODEL = "nvidia/nemotron-3-super-120b-a12b"
VERIFIER_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def _telemetry_total(telemetries: list[dict]) -> dict:
    """Aggregate Token Factory telemetry."""
    total_tokens = sum(
        item.get("total_tokens", 0)
        for item in telemetries
    )

    latency_ms = round(
        sum(item.get("latency_ms", 0.0) for item in telemetries),
        2,
    )

    costs = [
        item["cost_usd"]
        for item in telemetries
        if item.get("cost_usd") is not None
    ]

    cost_usd = (
        round(sum(costs), 8)
        if len(costs) == len(telemetries)
        else None
    )

    return {
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
    }


def _run_monolith_task(
    *,
    task,
    llm: LLMClient,
    verifier: Verifier,
) -> dict:
    """Run one task directly through the largest Nemotron, with one retry."""
    worker = Worker(
        llm,
        worker_id="monolith-super",
        model=MONOLITH_MODEL,
        strategy="direct",
    )

    attempts = []
    total_start = time.perf_counter()

    for attempt in range(1, 3):
        output = worker.execute(task)

        worker_telemetry = (
            worker.last_response.telemetry()
            if worker.last_response
            else {}
        )

        hidden_passed, hidden_reason = run_hidden_tests(
            task.id,
            output,
        )

        verdict = verifier.verify(
            task,
            "monolith-super",
            output,
        )

        # Hidden pytest is authoritative for benchmark code correctness.
        verdict.passed = hidden_passed
        verdict.reason = hidden_reason

        verifier_telemetry = (
            verifier.last_response.telemetry()
            if verifier.last_response
            else {}
        )

        attempts.append(
            {
                "attempt": attempt,
                "passed": verdict.passed,
                "worker_telemetry": worker_telemetry,
                "verifier_telemetry": verifier_telemetry,
                "reason": verdict.reason,
            }
        )

        if verdict.passed:
            break

    elapsed_ms = round(
        (time.perf_counter() - total_start) * 1000,
        2,
    )

    telemetries = []

    for attempt in attempts:
        telemetries.append(attempt["worker_telemetry"])
        telemetries.append(attempt["verifier_telemetry"])

    totals = _telemetry_total(telemetries)

    return {
        "model": MONOLITH_MODEL,
        "passed": attempts[-1]["passed"],
        "attempts": len(attempts),
        "retries": max(0, len(attempts) - 1),
        "latency_ms": elapsed_ms,
        "token_factory_latency_ms": totals["latency_ms"],
        "total_tokens": totals["total_tokens"],
        "token_factory_cost_usd": totals["cost_usd"],
        "attempt_details": attempts,
    }


def _write_csv(results: list[dict]) -> None:
    """Write one Monolith-vs-Market row per benchmark task."""
    fieldnames = [
        "task_id",
        "task_type",
        "monolith_model",
        "monolith_passed",
        "monolith_attempts",
        "monolith_retries",
        "monolith_tokens",
        "monolith_cost_usd",
        "monolith_latency_ms",
        "market_winner",
        "market_passed",
        "market_retries",
        "market_tokens",
        "market_cost_usd",
        "market_latency_ms",
        "market_price",
    ]

    with Path("benchmark_results.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        import csv

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for result in results:
            monolith = result["monolith"]
            market = result["market"]

            writer.writerow(
                {
                    "task_id": result["task_id"],
                    "task_type": result["task_type"],
                    "monolith_model": monolith["model"],
                    "monolith_passed": monolith["passed"],
                    "monolith_attempts": monolith["attempts"],
                    "monolith_retries": monolith["retries"],
                    "monolith_tokens": monolith["total_tokens"],
                    "monolith_cost_usd": (
                        monolith["token_factory_cost_usd"]
                    ),
                    "monolith_latency_ms": monolith["latency_ms"],
                    "market_winner": market["winner"],
                    "market_passed": market["passed"],
                    "market_retries": market["retries"],
                    "market_tokens": market["total_tokens"],
                    "market_cost_usd": (
                        market["token_factory_cost_usd"]
                    ),
                    "market_latency_ms": market["latency_ms"],
                    "market_price": market["price"],
                }
            )


def _summarize(results: list[dict]) -> dict:
    """Build the Monolith vs Market benchmark summary."""

    def mode_summary(mode: str) -> dict:
        entries = [result[mode] for result in results]

        passed = sum(
            1 for entry in entries if entry["passed"]
        )

        costs = [
            entry["token_factory_cost_usd"]
            for entry in entries
            if entry.get("token_factory_cost_usd") is not None
        ]

        return {
            "tasks": len(entries),
            "passed": passed,
            "failed": len(entries) - passed,
            "pass_rate": (
                round(passed / len(entries), 4)
                if entries
                else 0.0
            ),
            "total_token_factory_cost_usd": (
                round(sum(costs), 8)
                if len(costs) == len(entries)
                else None
            ),
            "average_token_factory_cost_usd": (
                round(sum(costs) / len(costs), 8)
                if len(costs) == len(entries) and entries
                else None
            ),
            "total_latency_ms": round(
                sum(entry["latency_ms"] for entry in entries),
                2,
            ),
            "average_latency_ms": (
                round(
                    sum(entry["latency_ms"] for entry in entries)
                    / len(entries),
                    2,
                )
                if entries
                else 0.0
            ),
            "total_retries": sum(
                entry["retries"] for entry in entries
            ),
        }

    return {
        "monolith": mode_summary("monolith"),
        "market": mode_summary("market"),
    }


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

        print("  Running monolith...")
        monolith = _run_monolith_task(
            task=task,
            llm=llm,
            verifier=verifier,
        )

        print(
            f"  Monolith: passed={monolith['passed']} "
            f"cost=${monolith['token_factory_cost_usd']} "
            f"time={monolith['latency_ms']}ms "
            f"retries={monolith['retries']}"
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

        hidden_passed, hidden_reason = run_hidden_tests(
            task.id,
            output,
        )

        verdict = verifier.verify(
            task,
            award.worker_id,
            output,
        )

        # Hidden pytest is authoritative for benchmark code correctness.
        verdict.passed = hidden_passed
        verdict.reason = hidden_reason

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

        worker_telemetry = (
            winner.last_response.telemetry()
            if winner.last_response
            else {}
        )

        verifier_telemetry = (
            verifier.last_response.telemetry()
            if verifier.last_response
            else {}
        )

        market_totals = _telemetry_total(
            [
                worker_telemetry,
                verifier_telemetry,
            ]
        )

        if verdict.passed:
            payment = market.settle_pass(
                winning_agent,
                award.price,
            )

            result = "PASS"
            market_retries = 0

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
            market_retries = 1

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

        market_result = {
            "winner": award.worker_id,
            "price": award.price,
            "passed": verdict.passed,
            "result": result,
            "retries": market_retries,
            "total_tokens": market_totals["total_tokens"],
            "token_factory_cost_usd": market_totals["cost_usd"],
            "latency_ms": market_totals["latency_ms"],
            "worker_telemetry": worker_telemetry,
            "verifier_telemetry": verifier_telemetry,
        }

        results.append(
            {
                "benchmark_id": benchmark_id,
                "task_id": task.id,
                "task_type": task.task_type.value,
                "monolith": monolith,
                "market": market_result,
            }
        )

        print(
            f"  Market: winner={award.worker_id} | "
            f"Price={award.price:.2f} | "
            f"Result={result} | "
            f"Cost=${market_result['token_factory_cost_usd']} | "
            f"Time={market_result['latency_ms']}ms"
        )

    summary = _summarize(results)

    passed = sum(
        1
        for result in results
        if result["market"]["passed"]
    )

    report = {
        "benchmark_id": benchmark_id,
        "completed": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "summary": summary,
        "results": results,
    }

    Path("benchmark_results.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    _write_csv(results)

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Completed: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(results) - passed}")
    print("Report: benchmark_results.json")

    for result in results:
        market = result["market"]
        print(
            f"{result['task_id']:12} "
            f"{result['task_type']:8} "
            f"{market['winner']:18} "
            f"${market['price']:.2f} "
            f"{'PASS' if market['passed'] else 'FAIL'}"
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
