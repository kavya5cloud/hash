"""Manager agent responsible for decomposing a goal into tasks."""

from __future__ import annotations

import json
import uuid

from ..llm import LLMClient, LLMResponse
from ..models import Goal, Task, TaskType


class Manager:
    """Use a Nemotron model to turn a goal into a structured task."""

    def __init__(self, llm: LLMClient, model: str) -> None:
        """Initialize the manager."""
        self.llm = llm
        self.model = model
        self.last_response: LLMResponse | None = None

    def create_task(self, goal: Goal) -> Task:
        """Decompose a Phase 1 coding goal into one task."""

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Manager agent in Hash. "
                    "Return ONLY valid JSON. "
                    "Create exactly one coding task from the user's goal. "
                    "The JSON must contain: prompt, task_type, budget, "
                    "acceptance_criteria. "
                    'task_type must be "code". '
                    "budget must be a positive number. "
                    "acceptance_criteria must be a JSON array of strings."
                ),
            },
            {
                "role": "user",
                "content": goal.prompt,
            },
        ]

        response = self.llm.chat(
            model=self.model,
            messages=messages,
            max_tokens=512,
        )
        self.last_response = response

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError:
            retry = self.llm.chat(
                model=self.model,
                messages=messages
                + [
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return ONLY the required JSON object."
                        ),
                    }
                ],
                max_tokens=512,
            )
            self.last_response = retry
            payload = json.loads(retry.content)

        return Task(
            id=str(uuid.uuid4()),
            goal_id=goal.id,
            prompt=payload["prompt"],
            task_type=TaskType.CODE,
            budget=float(payload["budget"]),
            acceptance_criteria=payload["acceptance_criteria"],
        )
