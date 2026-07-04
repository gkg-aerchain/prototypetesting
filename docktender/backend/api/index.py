"""Vercel Python serverless entry — exposes the FastAPI ASGI app.
All routes are rewritten to /api/index by vercel.json. The import goes through
app._boot so a cold-start import failure surfaces as a readable traceback
instead of an opaque FUNCTION_INVOCATION_FAILED."""
from app._boot import app  # noqa: F401
