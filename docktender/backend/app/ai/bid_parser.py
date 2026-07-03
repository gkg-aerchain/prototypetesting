"""AI bid ingestion — parse a pasted/uploaded yard quotation into canonical bid
lines using Claude with a strict tool schema. Output is always draft: lines carry
per-line confidence and are never counted until a human reviews them."""
from __future__ import annotations

from .client import get_client
from ..core.config import settings

# Strict tool: guarantees the model returns exactly this shape.
EMIT_BID_TOOL = {
    "name": "emit_bid",
    "description": "Emit the structured contents of a ship-repair yard quotation.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "currency": {"type": "string", "description": "ISO currency code, e.g. USD, EUR, SGD, TRY."},
            "dock_days": {"type": "integer", "description": "Quoted dock duration in days, 0 if not stated."},
            "exclusions_text": {"type": "string", "description": "Any stated exclusions, verbatim; empty if none."},
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "raw_text": {"type": "string", "description": "The line as it appears in the quote."},
                        "section_hint": {"type": "string", "description": "Best-guess spec section, e.g. 'General services', 'Steel renewals'. Empty if unclear."},
                        "uom": {"type": "string", "description": "Unit of measure if given (m2, t, ea, lot...). Empty if none."},
                        "qty": {"type": "number", "description": "Quantity, 0 if not stated."},
                        "rate": {"type": "number", "description": "Unit rate, 0 if not stated."},
                        "amount": {"type": "number", "description": "Line amount in the bid currency, 0 if not priced."},
                        "state": {"type": "string", "enum": ["priced", "included", "excluded", "unpriced"]},
                        "confidence": {"type": "number", "description": "0..1 confidence in this extraction."},
                    },
                    "required": ["raw_text", "section_hint", "uom", "qty", "rate", "amount", "state", "confidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["currency", "dock_days", "exclusions_text", "lines"],
        "additionalProperties": False,
    },
}

SYSTEM = (
    "You are a ship-repair estimating assistant helping a docking superintendent read a "
    "yard's dry-docking quotation. Extract every priced line, and every stated exclusion or "
    "'to be advised' item, into the emit_bid tool. Be faithful — do not invent amounts. "
    "Set state='excluded' for work the yard explicitly excludes, state='unpriced' for items "
    "marked TBA/to-be-advised, state='priced' for lines with an amount. Assign a realistic "
    "per-line confidence: high for clear line-item + amount, low for ambiguous or handwritten-"
    "looking text. Never merge distinct scope into one line."
)

CONFIDENCE_THRESHOLD = 0.75


def parse_quote(text: str) -> dict | None:
    """Parse quote text into a bid dict, or None if AI is unavailable.

    Returns {currency, dock_days, exclusions_text, lines:[...]} where each line
    also gets ai_confidence carried through for the review UI.
    """
    client = get_client()
    if client is None:
        return None

    # Chunk very long quotes to stay well within limits.
    chunks = _chunk(text, 30000)
    all_lines: list[dict] = []
    currency = "USD"
    dock_days = 0
    exclusions = []

    for chunk in chunks:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=8000,
            system=SYSTEM,
            tools=[EMIT_BID_TOOL],
            tool_choice={"type": "tool", "name": "emit_bid"},
            messages=[{"role": "user", "content": f"Quotation:\n\n{chunk}"}],
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        if not block:
            continue
        data = block.input
        currency = data.get("currency") or currency
        dock_days = data.get("dock_days") or dock_days
        if data.get("exclusions_text"):
            exclusions.append(data["exclusions_text"])
        for ln in data.get("lines", []):
            ln["ai_confidence"] = float(ln.get("confidence", 0.5))
            all_lines.append(ln)

    return {
        "currency": currency,
        "dock_days": dock_days,
        "exclusions_text": " ".join(exclusions),
        "lines": all_lines,
    }


def _chunk(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[i:i + size] for i in range(0, len(text), size)]
