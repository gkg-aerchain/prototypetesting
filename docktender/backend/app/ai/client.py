"""Anthropic client wrapper. Returns None when no API key is configured so the
rest of the app works without AI (endpoints return 503, tests skip)."""
from __future__ import annotations

from functools import lru_cache

from ..core.config import settings


@lru_cache
def get_client():
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def ai_available() -> bool:
    return get_client() is not None
