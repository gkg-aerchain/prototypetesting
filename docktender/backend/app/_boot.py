"""Cold-start boot shim for the serverless entrypoint.

Always exposes a top-level ``app`` (so Vercel's Python builder's static check
passes), but if importing the real application fails at cold start, ``app``
becomes a tiny ASGI app that returns the traceback as plain text instead of an
opaque FUNCTION_INVOCATION_FAILED."""
import traceback

try:
    from app.main import app  # noqa: F401
except Exception:  # pragma: no cover - diagnostic path
    _tb = traceback.format_exc()

    async def app(scope, receive, send):  # type: ignore[no-redef]
        if scope["type"] != "http":
            return
        body = ("DockTender API import failed:\n\n" + _tb).encode()
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})
