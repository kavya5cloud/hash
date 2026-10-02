"""Verifier agent responsible for independently checking worker output."""

from __future__ import annotations

import json

from ..llm import LLMClient, LLMResponse
from ..models import Task, Verdict


class Verifier:
    """Verify worker output using a separate Nemotron model."""

    def __init__(
        self,
        llm: LLMClient,
        model: str,
    ) -> None:
        """Initialize the verifier."""
        self.llm = llm
        self.model = model
        self.last_response: LLMResponse | None = None

    def verify(
        self,
        task: Task,
        worker_id: str,
        output: str,
    ) -> Verdict:
        """Return a structured pass/fail verdict."""

        acceptance = "\n".join(
            f"- {criterion}" for criterion in task.acceptance_criteria
        )

        response = self.llm.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an independent verifier in Hash. "
                        "Do not assume the worker is correct. "
                        "Evaluate the submitted output against the task "
                        "and acceptance criteria. "
                        "Return ONLY valid JSON with exactly these fields: "
                        "passed (boolean) and reason (string)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"TASK:\n{task.prompt}\n\n"
                        f"ACCEPTANCE CRITERIA:\n{acceptance}\n\n"
                        f"WORKER OUTPUT:\n{output}"
                    ),
                },
            ],
            max_tokens=1024,
        )

        self.last_response = response

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Verifier returned invalid JSON: {response.content!r}"
            ) from exc

        return Verdict(
            task_id=task.id,
            worker_id=worker_id,
            passed=bool(result["passed"]),
            reason=str(result["reason"]),
            output=output,
        )
