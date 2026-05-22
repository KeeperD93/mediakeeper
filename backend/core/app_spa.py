"""Serve the Vue 3 frontend (single-container) + SPA fallback."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("mediakeeper")


def _resolve_spa_file(frontend_dir: Path, full_path: str) -> Path | None:
    """Return a file inside frontend_dir, or None for fallback/index."""
    if not full_path:
        return None
    try:
        root = frontend_dir.resolve()
        candidate = (root / full_path).resolve()
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

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """SPA fallback — return index.html for any non-API route."""
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse as _JR
            return _JR(status_code=404, content={"detail": "Not Found"})
        candidate = _resolve_spa_file(frontend_dir, full_path)
        if candidate:
            return FileResponse(candidate)
        return FileResponse(frontend_dir / "index.html")
