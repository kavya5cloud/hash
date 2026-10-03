from hash_market.benchmark.tasks import benchmark_tasks
from hash_market.models import TaskType

def test_benchmark_has_20_tasks() -> None:
    tasks = benchmark_tasks()

    assert len(tasks) == 20
    assert len({task.id for task in tasks}) == 20


def test_benchmark_contains_only_coding_tasks() -> None:
    tasks = benchmark_tasks()

    assert all(task.task_type is TaskType.CODE for task in tasks)
    assert [task.id for task in tasks] == [
        f"code-{index:02d}"
        for index in range(1, 21)
    ]


def test_every_benchmark_task_has_positive_budget() -> None:
    tasks = benchmark_tasks()

    assert all(task.budget > 0 for task in tasks)
    assert all(task.acceptance_criteria for task in tasks)
