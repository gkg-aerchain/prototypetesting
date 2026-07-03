"""Vercel Python serverless entry — exposes the FastAPI ASGI app.
All routes are rewritten to /api/index by vercel.json."""
from app.main import app  # noqa: F401
