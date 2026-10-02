from hash_market.market import Market
from hash_market.models import Agent, Bid, Task, TaskType


def make_task() -> Task:
    return Task(
        id="task-1",
        goal_id="goal-1",
        prompt="Write a function",
        task_type=TaskType.CODE,
        budget=20.0,
    )


def make_agents() -> dict[str, Agent]:
    return {
        "worker-a": Agent(
            id="worker-a",
            name="Nano Worker",
            model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
            strategy="cheap",
            balance=100.0,
            reputation=80.0,
        ),
        "worker-b": Agent(
            id="worker-b",
            name="Lightning Worker",
            model="nvidia/Nemotron-3_5-Lightning",
            strategy="balanced",
            balance=100.0,
            reputation=60.0,
        ),
    }


def test_award_is_deterministic() -> None:
    market = Market()
    task = make_task()
    agents = make_agents()

    bids = [
        Bid(
            id="bid-a",
            task_id=task.id,
            worker_id="worker-a",
            price=10.0,
            estimated_time_seconds=5,
            plan="Use slicing",
        ),
        Bid(
            id="bid-b",
            task_id=task.id,
            worker_id="worker-b",
            price=15.0,
            estimated_time_seconds=4,
            plan="Use a loop",
        ),
    ]

    award = market.award(task, bids, agents)

    assert award.task_id == task.id
    assert award.worker_id == "worker-a"
    assert award.price == 10.0


def test_escrow_reduces_balance() -> None:
    market = Market()
    agent = make_agents()["worker-a"]

    market.reserve_escrow(agent, 25.0)

    assert agent.balance == 75.0


def test_success_increases_reputation() -> None:
    market = Market()
    agent = make_agents()["worker-a"]

    market.reserve_escrow(agent, 10.0)
    market.settle_pass(agent, 10.0)

    assert agent.reputation == 82.0


def test_failure_slashes_and_reduces_reputation() -> None:
    market = Market()
    agent = make_agents()["worker-a"]

    market.reserve_escrow(agent, 20.0)
    slash = market.settle_fail(agent, 20.0)

    assert slash == 5.0
    assert agent.reputation == 75.0
