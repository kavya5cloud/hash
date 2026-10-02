"""Worker agent responsible for bidding on and executing Hash tasks."""

from __future__ import annotations

import json
import uuid

from ..llm import LLMClient, LLMResponse
from ..models import Bid, Task


class Worker:
    """A model-backed Hash worker."""

    def __init__(
        self,
        llm: LLMClient,
        worker_id: str,
        model: str,
        strategy: str = "balanced",
    ) -> None:
        self.llm = llm
        self.worker_id = worker_id
        self.model = model
        self.strategy = strategy
        self.last_response: LLMResponse | None = None

    def _parse_bid(self, content: str) -> dict:
        """Parse a JSON bid from model output."""

        content = content.strip()

        # Direct JSON.
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Extract a JSON object embedded in prose or markdown.
        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end > start:
            candidate = content[start : end + 1]

            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        raise ValueError("Response did not contain valid bid JSON")

    def bid(self, task: Task) -> Bid:
        """Generate a sealed bid for a task."""

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a worker participating in the Hash "
                    "agent market. "
                    "Submit a sealed bid for the task. "
                    f"Your strategy is: {self.strategy}. "
                    "Return ONLY a JSON object. "
                    "Do not output reasoning, explanations, markdown, "
                    "code fences, or any text before or after the JSON. "
                    "The JSON must contain exactly these fields: "
                    "price, estimated_time_seconds, plan. "
                    "price must be a positive number and must not exceed "
                    "the task budget. "
                    "estimated_time_seconds must be positive. "
                    "plan must be a concise string."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TASK:\n{task.prompt}\n\n"
                    f"TASK BUDGET: {task.budget}\n\n"
                    "ACCEPTANCE CRITERIA:\n"
                    + "\n".join(
                        f"- {criterion}"
                        for criterion in task.acceptance_criteria
                    )
                ),
            },
        ]

        response = self.llm.chat(
            model=self.model,
            messages=messages,
            max_tokens=512,
        )
        self.last_response = response

        try:
            payload = self._parse_bid(response.content)
        except ValueError:
            retry = self.llm.chat(
                model=self.model,
                messages=messages
                + [
                    {
                        "role": "user",
                        "content": (
                            "INVALID FORMAT. Try again. "
                            "Your ENTIRE response must be exactly one "
                            "valid JSON object and nothing else. "
                            'Example: {"price": 10, '
                            '"estimated_time_seconds": 30, '
                            '"plan": "Use string slicing."}'
                        ),
                    }
                ],
                max_tokens=256,
            )

            self.last_response = retry
            payload = self._parse_bid(retry.content)

        price = float(payload["price"])

        if price <= 0 or price > task.budget:
            raise ValueError(
                f"Worker {self.worker_id} submitted invalid price: {price}"
            )

        estimated_time = float(payload["estimated_time_seconds"])

        if estimated_time <= 0:
            raise ValueError(
                f"Worker {self.worker_id} submitted invalid "
                f"estimated time: {estimated_time}"
            )

        return Bid(
            id=str(uuid.uuid4()),
            task_id=task.id,
            worker_id=self.worker_id,
            price=price,
            estimated_time_seconds=estimated_time,
            plan=str(payload["plan"]),
        )

    def execute(self, task: Task) -> str:
        """Execute the task and return the worker's output."""

        acceptance = "\n".join(
            f"- {criterion}" for criterion in task.acceptance_criteria
        )

        response = self.llm.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a worker agent in Hash. "
                        "Complete the assigned coding task. "
                        "Return the complete requested output and nothing "
                        "that is unrelated to the task."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"TASK:\n{task.prompt}\n\n"
                        f"ACCEPTANCE CRITERIA:\n{acceptance}"
                    ),
                },
            ],
            max_tokens=2048,
        )

        self.last_response = response
        return response.content
