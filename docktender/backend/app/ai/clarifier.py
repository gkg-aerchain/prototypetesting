"""Clarifier — drafts clarification questions from a bid's exclusions and
low-confidence lines. Output is a draft the superintendent edits before sending."""
from __future__ import annotations

from .client import get_client
from ..core.config import settings

EMIT_QUESTIONS_TOOL = {
    "name": "emit_questions",
    "description": "Emit clarification questions to send to a yard about its bid.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "reason": {"type": "string", "description": "Why this matters for the evaluation."},
                    },
                    "required": ["question", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
}

SYSTEM = (
    "You are a docking superintendent drafting clarification questions to a ship-repair yard "
    "before awarding a dry-docking tender. Given the yard's exclusions and any below-norm or "
    "low-confidence items, draft concise, specific questions that would close the commercial "
    "gaps — scope confirmation, unit-rate basis, what an exclusion covers, growth risk on "
    "to-be-confirmed quantities. Use correct ship-repair terminology. Keep each question to one "
    "clear ask."
)


def draft_questions(context: str) -> list[dict] | None:
    """Return [{question, reason}] drafts, or None if AI unavailable."""
    client = get_client()
    if client is None:
        return None
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2000,
        system=SYSTEM,
        tools=[EMIT_QUESTIONS_TOOL],
        tool_choice={"type": "tool", "name": "emit_questions"},
        messages=[{"role": "user", "content": context}],
    )
    block = next((b for b in resp.content if b.type == "tool_use"), None)
    return block.input.get("questions", []) if block else []
