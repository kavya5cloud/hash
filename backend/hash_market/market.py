"""Deterministic market rules for Hash."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Agent, Award, Bid, Task


@dataclass(frozen=True)
class MarketConfig:
    """Rules controlling the Hash market."""

    reputation_weight: float = 0.4
    price_weight: float = 0.6

    slash_fraction: float = 0.25
    reputation_gain: float = 2.0
    reputation_loss: float = 5.0

    max_bid_fraction: float = 1.0
    max_reputation: float = 100.0


class Market:
    """Deterministic engine for bids, awards, escrow and settlement."""

    def __init__(
        self,
        config: MarketConfig | None = None,
        treasury_balance: float = 0.0,
    ) -> None:
        self.config = config or MarketConfig()
        self.treasury_balance = treasury_balance

    def validate_bid(self, task: Task, bid: Bid) -> None:
        """Reject bids that violate deterministic market rules."""

        if bid.task_id != task.id:
            raise ValueError("Bid belongs to a different task")

        max_bid = task.budget * self.config.max_bid_fraction

        if bid.price > max_bid:
            raise ValueError("Bid exceeds task bid cap")

    def award(
        self,
        task: Task,
        bids: list[Bid],
        agents: dict[str, Agent],
    ) -> Award:
        """Select the winning bid deterministically."""

        if not bids:
            raise ValueError("Cannot award a task without bids")

        valid_bids: list[Bid] = []

        for bid in bids:
            self.validate_bid(task, bid)

            if bid.worker_id not in agents:
                raise ValueError(f"Unknown worker: {bid.worker_id}")

            valid_bids.append(bid)

        max_reputation = max(
            agents[bid.worker_id].reputation
            for bid in valid_bids
        )

        if max_reputation <= 0:
            max_reputation = 1.0

        max_price = max(
            bid.price
            for bid in valid_bids
        )

        if max_price <= 0:
            max_price = 1.0

        scored: list[tuple[float, Bid, float, float]] = []

        for bid in valid_bids:
            agent = agents[bid.worker_id]

            reputation_component = (
                agent.reputation / max_reputation
            )

            price_component = (
                1.0 - (bid.price / max_price)
            )

            score = (
                self.config.reputation_weight * reputation_component
                + self.config.price_weight * price_component
            )

            scored.append(
                (
                    score,
                    bid,
                    reputation_component,
                    price_component,
                )
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].price,
                item[1].id,
            )
        )

        score, winning_bid, reputation_component, price_component = (
            scored[0]
        )

        return Award(
            task_id=task.id,
            worker_id=winning_bid.worker_id,
            bid_id=winning_bid.id,
            score=score,
            reputation_component=reputation_component,
            price_component=price_component,
            price=winning_bid.price,
        )

    def reserve_escrow(
        self,
        agent: Agent,
        amount: float,
    ) -> None:
        """Move worker funds into market escrow."""

        if amount <= 0:
            raise ValueError("Escrow amount must be positive")

        if agent.balance < amount:
            raise ValueError(
                f"Insufficient balance for worker {agent.id}"
            )

        agent.balance -= amount
        self.treasury_balance += amount

    def settle_pass(
        self,
        agent: Agent,
        price: float,
    ) -> float:
        """Release escrow back to the worker after successful work."""

        if price <= 0:
            raise ValueError("Settlement amount must be positive")

        if self.treasury_balance < price:
            raise ValueError("Insufficient escrow balance")

        self.treasury_balance -= price
        agent.balance += price

        agent.reputation = min(
            self.config.max_reputation,
            agent.reputation + self.config.reputation_gain,
        )

        return price

    def settle_fail(
        self,
        agent: Agent,
        price: float,
    ) -> float:
        """Slash failed work and distribute the escrow deterministically."""

        if price <= 0:
            raise ValueError("Settlement amount must be positive")

        if self.treasury_balance < price:
            raise ValueError("Insufficient escrow balance")

        slash = price * self.config.slash_fraction
        refund = price - slash

        self.treasury_balance -= price

        # Return the non-slashed portion to the worker.
        agent.balance += refund

        agent.reputation = max(
            0.0,
            agent.reputation - self.config.reputation_loss,
        )

        return slash
