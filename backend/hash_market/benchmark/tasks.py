"""Benchmark tasks for evaluating the Hash market."""

from __future__ import annotations

from ..models import Task, TaskType


def benchmark_tasks() -> list[Task]:
    """Return the Phase 2 benchmark task set."""

    raw_tasks = [
        (
            "code-01",
            "Write a Python function add(a, b) that returns a + b.",
            TaskType.CODE,
        ),
        (
            "code-02",
            "Write a Python function is_even(n) that returns True when n is even.",
            TaskType.CODE,
        ),
        (
            "code-03",
            "Write a Python function reverse_string(s) that returns s reversed.",
            TaskType.CODE,
        ),
        (
            "code-04",
            "Write a Python function max_value(values) that returns the largest value.",
            TaskType.CODE,
        ),
        (
            "code-05",
            "Write a Python function count_vowels(s) that counts vowels.",
            TaskType.CODE,
        ),
        (
            "code-06",
            "Write a Python function factorial(n) for non-negative integers.",
            TaskType.CODE,
        ),
        (
            "code-07",
            "Write a Python function unique_items(values) preserving first occurrence order.",
            TaskType.CODE,
        ),
        (
            "copy-01",
            "Write a concise product tagline for an AI task marketplace.",
            TaskType.COPY,
        ),
        (
            "copy-02",
            "Write a short landing-page headline for a developer tool.",
            TaskType.COPY,
        ),
        (
            "copy-03",
            "Write a two-sentence description of an AI agent market.",
            TaskType.COPY,
        ),
        (
            "copy-04",
            "Write a concise call-to-action for trying an AI developer platform.",
            TaskType.COPY,
        ),
        (
            "copy-05",
            "Write a short professional announcement for a new AI product.",
            TaskType.COPY,
        ),
        (
            "copy-06",
            "Write three concise benefits of using specialized AI models.",
            TaskType.COPY,
        ),
        (
            "research-01",
            "List three factors to consider when evaluating an AI model for coding.",
            TaskType.RESEARCH,
        ),
        (
            "research-02",
            "Explain briefly why latency matters in an AI agent workflow.",
            TaskType.RESEARCH,
        ),
        (
            "research-03",
            "Explain the difference between model quality and model cost.",
            TaskType.RESEARCH,
        ),
        (
            "research-04",
            "List three risks of using one large model for every agent task.",
            TaskType.RESEARCH,
        ),
        (
            "research-05",
            "Explain why independent verification can improve agent reliability.",
            TaskType.RESEARCH,
        ),
        (
            "research-06",
            "List three useful metrics for an AI agent marketplace.",
            TaskType.RESEARCH,
        ),
        (
            "research-07",
            "Explain briefly how reputation can influence agent selection.",
            TaskType.RESEARCH,
        ),
    ]

    return [
        Task(
            id=task_id,
            goal_id="benchmark",
            prompt=prompt,
            task_type=task_type,
            budget=20.0,
            acceptance_criteria=[
                "Answer the requested task directly.",
                "Keep the response concise.",
            ],
        )
        for task_id, prompt, task_type in raw_tasks
    ]
