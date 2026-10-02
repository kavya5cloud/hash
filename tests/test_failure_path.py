from hash_market.market import Market
from hash_market.models import Agent


def test_failed_worker_is_slashed_and_reputation_drops() -> None:
    market = Market()
    agent = Agent(
        id="worker-fail",
        name="Failing Worker",
        model="test-model",
        strategy="balanced",
        balance=100.0,
        reputation=50.0,
    )

    market.reserve_escrow(agent, 20.0)

    assert agent.balance == 80.0
    assert market.treasury_balance == 20.0

    slash = market.settle_fail(agent, 20.0)

    assert slash == 5.0
    assert agent.balance == 95.0
    assert market.treasury_balance == 0.0
    assert agent.reputation == 45.0


def test_failed_worker_cannot_be_slashed_twice() -> None:
    market = Market()
    agent = Agent(
        id="worker-fail",
        name="Failing Worker",
        model="test-model",
        strategy="balanced",
        balance=100.0,
        reputation=50.0,
    )

    market.reserve_escrow(agent, 20.0)
    market.settle_fail(agent, 20.0)

    try:
        market.settle_fail(agent, 20.0)
    except ValueError as exc:
        assert "Insufficient escrow" in str(exc)
    else:
        raise AssertionError("Expected second settlement to fail")
