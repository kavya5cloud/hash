import pytest

from hash_market.market import Market, MarketConfig
from hash_market.models import Bid, Task, TaskType


def make_task() -> Task:
    return Task(
        id="task-cap",
        goal_id="goal-cap",
        prompt="Test task",
        task_type=TaskType.CODE,
        budget=20.0,
    )


def make_bid(price: float) -> Bid:
    return Bid(
        id="bid-cap",
        task_id="task-cap",
        worker_id="worker-1",
        price=price,
        estimated_time_seconds=10.0,
        plan="Complete the task.",
    )


def test_bid_at_budget_cap_is_allowed() -> None:
    market = Market()
    task = make_task()

    market.validate_bid(task, make_bid(20.0))


def test_bid_above_budget_cap_is_rejected() -> None:
    market = Market()
    task = make_task()

    with pytest.raises(ValueError, match="bid cap"):
        market.validate_bid(task, make_bid(20.01))


def test_custom_bid_fraction_cap() -> None:
    market = Market(
        MarketConfig(
            max_bid_fraction=0.5,
        )
    )

    task = make_task()

    market.validate_bid(task, make_bid(10.0))

    with pytest.raises(ValueError, match="bid cap"):
        market.validate_bid(task, make_bid(10.01))


def test_reputation_never_exceeds_100() -> None:
    from hash_market.models import Agent

    market = Market()

    agent = Agent(
        id="worker-1",
        name="Worker",
        model="test-model",
        strategy="balanced",
        balance=100.0,
        reputation=99.0,
    )

    market.reserve_escrow(agent, 10.0)
    market.settle_pass(agent, 10.0)

    assert agent.reputation == 100.0


def test_reputation_never_goes_below_zero() -> None:
    from hash_market.models import Agent

    market = Market()

    agent = Agent(
        id="worker-1",
        name="Worker",
        model="test-model",
        strategy="balanced",
        balance=100.0,
        reputation=2.0,
    )

    market.reserve_escrow(agent, 10.0)
    market.settle_fail(agent, 10.0)

    assert agent.reputation == 0.0
