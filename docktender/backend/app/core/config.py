"""Runtime configuration. Mirrors the PassagePilot pattern:
- DATABASE_URL env drives persistence; SQLite for the demo.
- On Vercel (VERCEL env set) fall back to an ephemeral /tmp SQLite file.
- DEMO_SEED (default 1) seeds the demo tenant at boot when the URL is SQLite.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DockTender"
    version: str = "0.1.0"

    # Persistence
    database_url: str = "sqlite:///./docktender.db"

    # Auth
    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # one week

    # Demo seeding
    demo_seed: bool = True

    # AI
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"

    # Optional integration: PassagePilot routing API for deviation distance
    routing_api_url: str | None = None

    def resolve_database_url(self) -> str:
        """On Vercel the only writable path is /tmp; use an ephemeral SQLite file
        there unless an explicit external DATABASE_URL was provided."""
        url = self.database_url
        if os.environ.get("VERCEL") and url.startswith("sqlite") and "/tmp/" not in url:
            return "sqlite:////tmp/docktender.db"
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.resolve_database_url().startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
