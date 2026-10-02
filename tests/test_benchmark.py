from hash_market.benchmark.tasks import benchmark_tasks
from hash_market.models import TaskType


def test_benchmark_has_20_tasks() -> None:
    tasks = benchmark_tasks()

    assert len(tasks) == 20
    assert len({task.id for task in tasks}) == 20


def test_benchmark_covers_required_task_types() -> None:
    tasks = benchmark_tasks()

    task_types = {task.task_type for task in tasks}

    assert TaskType.CODE in task_types
    assert TaskType.COPY in task_types
    assert TaskType.RESEARCH in task_types


def test_every_benchmark_task_has_positive_budget() -> None:
    tasks = benchmark_tasks()

    assert all(task.budget > 0 for task in tasks)
    assert all(task.acceptance_criteria for task in tasks)
