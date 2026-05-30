"""SPA static file containment + 404-fallback routing tests."""
from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from core.app_spa import _resolve_spa_file, register_spa


def test_resolve_spa_file_accepts_file_inside_root(tmp_path):
    root = tmp_path / "frontend-dist"
    root.mkdir()
    asset = root / "asset.txt"
    asset.write_text("ok", encoding="utf-8")

    assert _resolve_spa_file(root, "asset.txt") == asset.resolve()


def test_resolve_spa_file_rejects_prefix_sibling_escape(tmp_path):
    root = tmp_path / "frontend-dist"
    root.mkdir()
    sibling = tmp_path / "frontend-dist-evil"
    sibling.mkdir()
    (sibling / "asset.txt").write_text("nope", encoding="utf-8")

    assert _resolve_spa_file(root, "../frontend-dist-evil/asset.txt") is None


def _build_spa_app(tmp_path):
    """Build a FastAPI app with the SPA fallback wired against a temp build dir."""
    dist = tmp_path / "frontend-dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    (dist / "assets" / "app-REALHASH.js").write_text("console.log(1)", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    register_spa(app, dist_dir=dist)
    return app


def test_spa_fallback_serves_index_for_client_routes(tmp_path):
    """An unmatched non-API GET resolves to the SPA shell (client-side routing)."""
    client = TestClient(_build_spa_app(tmp_path))

    resp = client.get("/portal/some/client/route")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_spa_fallback_keeps_json_404_for_api_miss(tmp_path):
    """An unmatched /api/* path must stay a JSON 404, never the HTML shell."""
    client = TestClient(_build_spa_app(tmp_path))

    resp = client.get("/api/does-not-exist")

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def test_spa_fallback_does_not_mask_missing_hashed_asset(tmp_path):
    """A missing /assets/* file must 404, not be served index.html (200) — else a
    stale hashed-asset request after redeploy would be parsed as JS and cached by
    the service worker, persisting a broken state. The real asset still resolves."""
    client = TestClient(_build_spa_app(tmp_path))

    missing = client.get("/assets/app-OLDHASH.js")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")

    real = client.get("/assets/app-REALHASH.js")
    assert real.status_code == 200


def test_register_spa_does_not_shadow_per_route_limits(tmp_path):
    """The SPA fallback must be a 404 exception handler, NOT a catch-all route:
    a ``/{full_path:path}`` route would shadow slowapi's per-route limit lookup
    (the bug this design fixes), making every /api route fall back to the global
    default limit."""
    app = _build_spa_app(tmp_path)

    route_paths = {getattr(r, "path", None) for r in app.routes}
    assert "/{full_path:path}" not in route_paths
    assert 404 in app.exception_handlers
