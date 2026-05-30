"""Serve the Vue 3 frontend (single-container) + SPA fallback."""
import logging
import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("mediakeeper")

# Vite produces hash-suffixed asset names: ``index-DXyZ_abc.js``,
# ``logo-x123.png``, etc. The first character cannot be ``.`` so we
# reject dotfiles (``.env``, ``.htaccess``, …) outright; subsequent
# characters allow the conventional hash + extension separators.
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")


def _resolve_spa_file(frontend_dir: Path, full_path: str) -> Path | None:
    """Return a file inside frontend_dir, or None for fallback/index."""
    if not full_path:
        return None
    # Strict per-segment whitelist. Anything that does not match the
    # ``Vite-built asset`` shape (alphanumerics + ``._-``, no dot
    # prefix) is refused before it reaches ``Path.resolve()``. This
    # closes the ``py/path-injection`` sink CodeQL flags here (it
    # cannot trace our ``relative_to(root)`` containment guard below)
    # and adds genuine defence in depth — an attacker cannot reach
    # the syscall layer with ``..``, absolute paths, NUL bytes,
    # spaces or dotfiles.
    raw_parts = full_path.replace("\\", "/").split("/")
    safe_parts: list[str] = []
    for part in raw_parts:
        if not _SAFE_SEGMENT.fullmatch(part):
            return None
        safe_parts.append(part)
    if not safe_parts:
        return None
    try:
        root = frontend_dir.resolve()
        candidate = root.joinpath(*safe_parts).resolve()
    except (ValueError, OSError, RuntimeError):
        return None
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def register_spa(app: FastAPI) -> None:
    """Mount the Vite build + SPA fallback route if frontend-dist/ exists."""
    app_root = Path(__file__).resolve().parent.parent.parent
    vue_dist = app_root / "frontend-dist"

    if vue_dist.is_dir() and (vue_dist / "index.html").is_file():
        frontend_dir = vue_dist
        logger.info(f"Serving Vue 3 frontend from {frontend_dir}")
    else:
        logger.warning("No frontend directory found!")
        return

    @app.get("/login.html")
    async def serve_login_compat():
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)

    for subdir in ("assets",):
        subpath = frontend_dir / subdir
        if subpath.is_dir():
            app.mount(f"/{subdir}", StaticFiles(directory=str(subpath)), name=f"static_{subdir}")

    # SPA fallback as a 404 handler instead of a ``/{full_path:path}`` catch-all
    # route. A catch-all matches every path — including ``/api/*`` — and, being
    # registered last, shadows slowapi's per-route limit lookup: its middleware
    # (``_find_route_handler`` keeps the LAST full match) resolves every request
    # to this handler, so per-route ``@limiter.limit`` / ``@limiter.exempt`` are
    # never applied. Serving the SPA from the 404 path leaves the route table
    # clean, so each API route keeps its own rate limit.
    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        """Serve index.html for unmatched non-API GET/HEAD routes (client-side
        routing); every other 404 keeps the normal JSON error."""
        if request.method in ("GET", "HEAD") and not request.url.path.startswith("/api/"):
            candidate = _resolve_spa_file(frontend_dir, request.url.path.lstrip("/"))
            if candidate:
                return FileResponse(candidate)
            return FileResponse(frontend_dir / "index.html")
        return JSONResponse(status_code=404, content={"detail": getattr(exc, "detail", "Not Found")})
