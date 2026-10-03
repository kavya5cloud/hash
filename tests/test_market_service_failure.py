from hash_market.ledger import Ledger
from hash_market.market_service import run_market
from hash_market.models import Goal, Task, TaskType


class FakeResponse:
    def __init__(self, content: str):
        self.content = content

    def telemetry(self):
        return {
            "model": "fake-model",
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20,
            "latency_ms": 1.0,
        }


class FakeLLM:
    def chat(self, *, model, messages, max_tokens=1024):
        prompt = "\n".join(message["content"] for message in messages)

        if "sealed bid" in prompt.lower():
            return FakeResponse(
                '{"price": 1.0, "estimated_time_seconds": 5, '
                '"plan": "implement the task"}'
            )

        if "independent verifier" in prompt.lower():
            return FakeResponse(
                '{"passed": false, "reason": "intentional test failure"}'
            )

        return FakeResponse("bad implementation")


def test_market_service_slashes_and_reposts_on_verifier_failure(tmp_path):
    ledger = Ledger(str(tmp_path / "hash.db"))

    goal = Goal(
        id="goal-failure",
        prompt="Write a Python function called multiply(a, b).",
        budget=100.0,
    )

    task = Task(
        id="task-failure",
        goal_id=goal.id,
        prompt=goal.prompt,
        task_type=TaskType.CODE,
        budget=5.0,
        acceptance_criteria=["Function returns a * b."],
    )

    result = run_market(
        goal=goal,
        task=task,
        llm=FakeLLM(),
        ledger=ledger,
    )

    events = result.events
    event_types = [event["event_type"] for event in events]

    assert "task_awarded" in event_types
    assert "escrow_reserved" in event_types
    assert "verdict" in event_types
    assert "payment_slashed" in event_types
    assert "reputation_updated" in event_types
    assert "task_reposted" in event_types

    # The failed task must actually be reposted and awarded again.
    assert event_types.count("task_awarded") == 2
    assert event_types.count("escrow_reserved") == 2
    assert event_types.count("verdict") == 2

    first_award = next(
        event["data"]
        for event in events
        if event["event_type"] == "task_awarded"
    )
    second_award = [
        event["data"]
        for event in events
        if event["event_type"] == "task_awarded"
    ][1]

    assert first_award["worker_id"] in {
        "worker-nano",
        "worker-lightning",
        "worker-super",
    }
    assert second_award["worker_id"] in {
        "worker-nano",
        "worker-lightning",
        "worker-super",
    }
    assert second_award["worker_id"] != first_award["worker_id"]

    verdict = next(
        event["data"]
        for event in events
        if event["event_type"] == "verdict"
    )
    assert verdict["passed"] is False

    slash = next(
        event["data"]
        for event in events
        if event["event_type"] == "payment_slashed"
    )
    assert slash["amount"] == 0.25

    reputation = next(
        event["data"]
        for event in events
        if event["event_type"] == "reputation_updated"
    )
    assert reputation["result"] == "fail"
    assert reputation["reputation"] == 45.0

    ledger.close()
