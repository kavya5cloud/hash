from hash_market.market import Market
from hash_market.models import Agent


def make_agent() -> Agent:
    return Agent(
        id="worker-1",
        name="Test Worker",
        model="test-model",
        strategy="balanced",
        balance=100.0,
        reputation=50.0,
    )


def test_pass_returns_escrow_to_worker() -> None:
    market = Market()
    agent = make_agent()

    market.reserve_escrow(agent, 10.0)

    assert agent.balance == 90.0
    assert market.treasury_balance == 10.0

    payment = market.settle_pass(agent, 10.0)

    assert payment == 10.0
    assert agent.balance == 100.0
    assert market.treasury_balance == 0.0
    assert agent.reputation == 52.0


def test_failure_refunds_remainder_and_slashes() -> None:
    market = Market()
    agent = make_agent()

    market.reserve_escrow(agent, 20.0)

    slash = market.settle_fail(agent, 20.0)

    assert slash == 5.0
    assert agent.balance == 95.0
    assert market.treasury_balance == 0.0
    assert agent.reputation == 45.0


def test_cannot_escrow_more_than_balance() -> None:
    market = Market()
    agent = make_agent()

    try:
        market.reserve_escrow(agent, 101.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected insufficient balance error")


def test_cannot_settle_without_escrow() -> None:
    market = Market()
    agent = make_agent()

    try:
        market.settle_pass(agent, 10.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected insufficient escrow error")
