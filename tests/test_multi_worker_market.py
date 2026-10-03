from hash_market.market import Market
from hash_market.models import Bid, Task, TaskType
from hash_market.participants import phase2_agents


def test_multiple_workers_can_compete() -> None:
    market = Market()
    agents = phase2_agents()

    task = Task(
        id="task-market-1",
        goal_id="goal-1",
        prompt="Write reverse_string",
        task_type=TaskType.CODE,
        budget=20.0,
    )

    bids = [
        Bid(
            id="sealed-nano",
            task_id=task.id,
            worker_id="worker-nano",
            price=8.0,
            estimated_time_seconds=5.0,
            plan="Use string slicing.",
        ),
        Bid(
            id="sealed-lightning",
            task_id=task.id,
            worker_id="worker-lightning",
            price=12.0,
            estimated_time_seconds=4.0,
            plan="Use a direct reverse operation.",
        ),
        Bid(
            id="sealed-super",
            task_id=task.id,
            worker_id="worker-super",
            price=16.0,
            estimated_time_seconds=3.0,
            plan="Produce and verify a concise implementation.",
        ),
    ]

    award = market.award(task, bids, agents)

    assert award.task_id == task.id
    assert award.worker_id in agents
    assert award.price <= task.budget


def test_worker_balances_are_unchanged_before_escrow() -> None:
    agents = phase2_agents()

    assert all(agent.balance == 100.0 for agent in agents.values())
