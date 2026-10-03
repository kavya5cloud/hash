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


def test_guardrails_enforce_round_retry_output_and_budget_limits():
    from hash_market.guardrails import (
        GuardrailConfig,
        validate_budget,
        validate_output,
        validate_retry,
        validate_round,
    )

    config = GuardrailConfig(
        max_rounds=2,
        max_retries=1,
        max_output_chars=10,
        max_task_budget=100.0,
    )

    validate_round(2, config)
    validate_retry(1, config)
    validate_output("1234567890", config)
    validate_budget(100.0, config)

    import pytest

    with pytest.raises(ValueError):
        validate_round(3, config)

    with pytest.raises(ValueError):
        validate_retry(2, config)

    with pytest.raises(ValueError):
        validate_output("12345678901", config)

    with pytest.raises(ValueError):
        validate_budget(101.0, config)
