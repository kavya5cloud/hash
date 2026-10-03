"""Build a benchmark evidence report from the Hash ledger."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path


def build_report(
    db_path: str = "hash.db",
    results_path: str = "benchmark_results.json",
) -> dict:
    """Build an evidence report for the latest Monolith-vs-Market benchmark."""

    results_file = Path(results_path)

    if not results_file.exists():
        raise FileNotFoundError(
            f"Benchmark results not found: {results_path}"
        )

    benchmark_results = json.loads(
        results_file.read_text(encoding="utf-8")
    )

    benchmark_id = benchmark_results.get("benchmark_id")

    if not benchmark_id:
        raise ValueError(
            "benchmark_results.json does not contain benchmark_id"
        )

    results = benchmark_results.get("results", [])
    summary = benchmark_results.get("summary", {})

    # Preserve market evidence from the append-only event ledger.
    connection = sqlite3.connect(db_path)

    rows = connection.execute(
        """
        SELECT run_id, event_type, data
        FROM events
        ORDER BY id ASC
        """
    ).fetchall()

    connection.close()

    runs: dict[str, dict] = {}

    for run_id, event_type, raw_data in rows:
        if run_id not in runs:
            runs[run_id] = {
                "bids": [],
                "award": None,
                "work": None,
                "verdict": None,
            }

        data = json.loads(raw_data)

        if event_type == "sealed_bid_submitted":
            runs[run_id]["bids"].append(data)

        elif event_type == "task_awarded":
            runs[run_id]["award"] = data

        elif event_type == "work_submitted":
            runs[run_id]["work"] = data

        elif event_type == "verdict":
            runs[run_id]["verdict"] = data

    benchmark_runs = {
        run_id: run
        for run_id, run in runs.items()
        if run["award"]
        and run["award"].get("benchmark_id") == benchmark_id
    }

    market_ledger_tasks = []

    for run_id, run in benchmark_runs.items():
        award = run["award"]

        task = {
            "run_id": run_id,
            "task_id": award["task_id"],
            "winner": award["worker_id"],
            "winning_price": award["price"],
            "score": award["score"],
            "reputation_component": award.get(
                "reputation_component"
            ),
            "price_component": award.get(
                "price_component"
            ),
            "passed": (
                run["verdict"]["passed"]
                if run["verdict"]
                else False
            ),
            "bids": run["bids"],
        }

        if run["work"]:
            task["worker_telemetry"] = run["work"].get(
                "telemetry",
                {},
            )

        if run["verdict"]:
            task["verifier_telemetry"] = run["verdict"].get(
                "telemetry",
                {},
            )

        market_ledger_tasks.append(task)

    winner_counts = Counter(
        task["winner"]
        for task in market_ledger_tasks
    )

    return {
        "benchmark_id": benchmark_id,
        "benchmark": {
            "completed": benchmark_results.get("completed", 0),
            "passed": benchmark_results.get("passed", 0),
            "failed": benchmark_results.get("failed", 0),
        },
        "summary": summary,
        "comparison": {
            "monolith": summary.get("monolith", {}),
            "market": summary.get("market", {}),
        },
        "results": results,
        "market_ledger": {
            "runs": len(market_ledger_tasks),
            "winner_counts": dict(winner_counts),
            "tasks": market_ledger_tasks,
        },
    }


if __name__ == "__main__":
    report = build_report()

    Path("benchmark_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Created benchmark_report.json")
    print("\n=== BENCHMARK SUMMARY ===")
    print(json.dumps(report["benchmark"], indent=2))

    print("\n=== MONOLITH ===")
    print(json.dumps(
        report["comparison"]["monolith"],
        indent=2,
    ))

    print("\n=== MARKET ===")
    print(json.dumps(
        report["comparison"]["market"],
        indent=2,
    ))

    print("\n=== MARKET LEDGER WINNERS ===")
    print(json.dumps(
        report["market_ledger"]["winner_counts"],
        indent=2,
    ))
