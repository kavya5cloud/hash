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
            "Write a Python function count_vowels(s) that returns the number of vowels in a string. Treat a, e, i, o, u as vowels and ignore case.",
            TaskType.CODE,
        ),
        (
            "code-05",
            "Write a Python function unique_items(values) that removes duplicates while preserving the order of first occurrence.",
            TaskType.CODE,
        ),
        (
            "code-06",
            "Write a Python function second_largest(values) that returns the second-largest distinct value in a non-empty list. Return None if there is no second distinct value.",
            TaskType.CODE,
        ),
        (
            "code-07",
            "Write a Python function is_palindrome(s) that returns True when s reads the same forwards and backwards, ignoring case and non-alphanumeric characters.",
            TaskType.CODE,
        ),
        (
            "code-08",
            "Write a Python function word_frequency(text) that returns a dictionary mapping each whitespace-separated word to its count. Treat words case-insensitively.",
            TaskType.CODE,
        ),
        (
            "code-09",
            "Write a Python function merge_sorted(a, b) that merges two already-sorted lists into one sorted list without using sorted() or sort().",
            TaskType.CODE,
        ),
        (
            "code-10",
            "Write a Python function binary_search(values, target) that returns the index of target in a sorted list, or -1 when it is absent.",
            TaskType.CODE,
        ),
        (
            "code-11",
            "Write a Python function rotate_list(values, k) that rotates a list to the right by k positions. Handle k larger than the list length and an empty list.",
            TaskType.CODE,
        ),
        (
            "code-12",
            "Write a Python function flatten_one_level(values) that flattens exactly one level of nested lists. Example: [1, [2, 3], [4]] becomes [1, 2, 3, 4].",
            TaskType.CODE,
        ),
        (
            "code-13",
            "Write a Python function first_non_repeating(s) that returns the first character occurring exactly once, or None if every character repeats. Treat uppercase and lowercase as distinct.",
            TaskType.CODE,
        ),
        (
            "code-14",
            "Write a Python function two_sum(values, target) that returns indices of two distinct elements whose values add to target, or None if no pair exists.",
            TaskType.CODE,
        ),
        (
            "code-15",
            "Write a Python function longest_increasing_run(values) that returns the length of the longest contiguous strictly increasing run. Return 0 for an empty list.",
            TaskType.CODE,
        ),
        (
            "code-16",
            "Write a Python function valid_parentheses(s) that returns True when every (), [], and {} bracket is correctly opened and closed in order.",
            TaskType.CODE,
        ),
        (
            "code-17",
            "Write a Python function group_anagrams(words) that groups words that are anagrams of each other. Preserve the original word order within each group.",
            TaskType.CODE,
        ),
        (
            "code-18",
            "Write a Python function shortest_path_grid(grid) that returns the minimum number of moves from the top-left to the bottom-right of a grid, moving up, down, left, or right through cells containing 0. Cells containing 1 are blocked. Return -1 when unreachable.",
            TaskType.CODE,
        ),
        (
            "code-19",
            "Fix a Python function that should return the first duplicate value in a list, but currently returns the first value that appears only once. Rewrite the function so it returns the first value whose second occurrence is encountered while scanning left to right, or None if there is no duplicate.",
            TaskType.CODE,
        ),
        (
            "code-20",
            "Write a Python function top_k_frequent(values, k) that returns the k most frequent values, ordered by decreasing frequency and then by first occurrence in the input when frequencies tie.",
            TaskType.CODE,
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
