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
    """Build a scoped evidence report for the latest benchmark."""

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

    connection = sqlite3.connect(db_path)

    rows = connection.execute(
        """
        SELECT run_id, event_type, data
        FROM events
        ORDER BY id ASC
        """
    ).fetchall()

    connection.close()

    # First collect ALL events by task run.
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

    # Only keep runs whose award belongs to this benchmark.
    benchmark_runs = {
        run_id: run
        for run_id, run in runs.items()
        if run["award"]
        and run["award"].get("benchmark_id") == benchmark_id
    }

    tasks = []

    for run_id, run in benchmark_runs.items():
        award = run["award"]

        winner = award["worker_id"]

        task = {
            "run_id": run_id,
            "task_id": award["task_id"],
            "winner": winner,
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

        tasks.append(task)

    winner_counts = Counter(
        task["winner"]
        for task in tasks
    )

    category_counts: dict[str, dict] = {}

    for task in tasks:
        task_id = task["task_id"]

        if task_id.startswith("code-"):
            category = "code"
        elif task_id.startswith("copy-"):
            category = "copy"
        elif task_id.startswith("research-"):
            category = "research"
        else:
            category = "other"

        if category not in category_counts:
            category_counts[category] = {
                "tasks": 0,
                "passed": 0,
            }

        category_counts[category]["tasks"] += 1

        if task["passed"]:
            category_counts[category]["passed"] += 1

    return {
        "benchmark_id": benchmark_id,
        "summary": {
            "tasks": len(tasks),
            "passed": sum(
                1 for task in tasks if task["passed"]
            ),
            "failed": sum(
                1 for task in tasks if not task["passed"]
            ),
        },
        "worker_stats": {
            worker: {
                "wins": wins,
            }
            for worker, wins in winner_counts.items()
        },
        "category_stats": category_counts,
        "tasks": tasks,
    }


if __name__ == "__main__":
    report = build_report()

    Path("benchmark_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Created benchmark_report.json")
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["worker_stats"], indent=2))
