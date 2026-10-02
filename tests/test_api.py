from fastapi.testclient import TestClient

from hash_market.api import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agents() -> None:
    response = client.get("/agents")

    assert response.status_code == 200

    agents = response.json()

    assert len(agents) == 3
    assert {
        agent["model"]
        for agent in agents
    } == {
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        "nvidia/Nemotron-3_5-Lightning",
        "nvidia/nemotron-3-super-120b-a12b",
    }


def test_benchmark() -> None:
    response = client.get("/benchmark")

    assert response.status_code == 200

    payload = response.json()

    assert payload["completed"] == 20
    assert payload["passed"] == 20
    assert payload["failed"] == 0


def test_run_detail() -> None:
    run_id = (
        "80a2fe40-5e6c-4adf-90ca-a0d7cc505215"
    )

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200

    payload = response.json()

    assert payload["run_id"] == run_id
    assert payload["status"] == "completed"
    assert len(payload["tasks"]) == 1
    assert payload["bids"] == []
    assert payload["verdicts"][0]["passed"] is True
    assert payload["output"]
    assert payload["telemetry"]["manager"]["model"]
    assert payload["telemetry"]["worker"]["model"]
    assert payload["telemetry"]["verifier"]["model"]
    assert payload["cost_summary"]["total_tokens"] == 1078


def test_run_events() -> None:
    run_id = (
        "80a2fe40-5e6c-4adf-90ca-a0d7cc505215"
    )

    response = client.get(
        f"/runs/{run_id}/events"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/event-stream"
    )

    body = response.text

    assert "goal_created" in body
    assert "task_posted" in body
    assert "work_submitted" in body
    assert "verdict" in body
    assert "goal_completed" in body
    assert "event: end" in body


def test_models_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    response = client.get("/models")

    assert response.status_code == 503
