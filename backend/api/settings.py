import logging
import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from core.database import get_db
from core.http_client import get_internal_client, get_external_client
from api.auth import get_current_user
from models.user import User
from services.settings import (
    TOOLS_DEFINITION,
    get_settings_map,
    get_tools_config,
    get_active_media_source,
    set_settings_map,
)
from services.media_manager import get_categories, save_categories
from services.path_config import get_configured_path_roots, validate_path_in_roots
from api.settings_dashboard import router as dashboard_router

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger("mediakeeper.api.settings")


class ToolSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ``extra="forbid"`` rejects any key not listed here with a 422 — keep
    # this schema in sync with the field keys in TOOLS_DEFINITION. Fields
    # default to None so save_tool can distinguish "not sent" (preserve
    # existing value) from "sent as empty" (wipe the value).
    enabled:     bool | None = None
    url:         str  | None = None
    public_url:  str  | None = None   # Emby: optional HTTPS URL for user-facing links
    api_key:     str  | None = None
    username:    str  | None = None   # OpenSubtitles
    password:    str  | None = None   # OpenSubtitles


class MediaFolderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str | None = None
    label: str
    path: str


class MediaFoldersSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folders: list[MediaFolderRequest] = []


def _slugify_folder_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^a-z0-9]+", "", ascii_value.lower())
    return key or "media"


def _normalize_media_folders(raw_folders: list[MediaFolderRequest]) -> list[dict]:
    folders: list[dict] = []
    seen_keys: set[str] = set()

    for folder in raw_folders:
        path = folder.path.strip()
        if not path:
            continue

        label = folder.label.strip() or path
        raw_key = (folder.key or "").strip()
        if not raw_key or raw_key.upper().startswith("MEDIA_"):
            raw_key = label

        key = _slugify_folder_key(raw_key)
        if key in seen_keys:
            suffix = 2
            while f"{key}{suffix}" in seen_keys:
                suffix += 1
            key = f"{key}{suffix}"
        seen_keys.add(key)
        folders.append({
            "key": key,
            "label": label,
            "path": path,
        })

    return folders


def _validate_media_folder_paths(folders: list[dict]) -> list[dict]:
    validated: list[dict] = []
    roots = get_configured_path_roots()
    for folder in folders:
        if roots:
            resolved, error = validate_path_in_roots(
                folder["path"],
                allow_missing=True,
                must_be_dir=True,
                roots=roots,
                label="Media folder",
            )
            if error:
                raise HTTPException(status_code=400, detail=error)
        else:
            try:
                resolved = Path(folder["path"]).expanduser().resolve(strict=False)
            except (ValueError, OSError, RuntimeError):
                raise HTTPException(status_code=400, detail="invalid_path") from None
        validated.append({**folder, "path": str(resolved)})
    return validated


@router.get("/tools/definition")
async def tools_definition(_: User = Depends(get_current_user)):
    """Return the static definition of every supported tool."""
    return TOOLS_DEFINITION


@router.get("/tools")
async def get_tools(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Return every tool's full config as stored in the DB."""
    return await get_tools_config(db, mask_secrets=True)


@router.post("/tools/{tool_key}")
async def save_tool(
    tool_key: str,
    req:      ToolSaveRequest,
    db:       AsyncSession = Depends(get_db),
    _:        User         = Depends(get_current_user),
):
    """Save a tool's config. For a media source, disable the other sources."""
    if tool_key not in TOOLS_DEFINITION:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_key}'")

    tool_def = TOOLS_DEFINITION[tool_key]
    sent = req.model_fields_set  # Only update fields the client explicitly sent

    # Only one media source can be active at a time
    updates = {}
    if tool_def["type"] == "source_media" and req.enabled:
        for other_key, other_def in TOOLS_DEFINITION.items():
            if other_def["type"] == "source_media" and other_key != tool_key:
                updates[f"{other_key}.enabled"] = "false"

    if "enabled" in sent:
        updates[f"{tool_key}.enabled"] = "true" if req.enabled else "false"

    for field in tool_def["fields"]:
        fk = field["key"]
        if fk in sent:
            val = getattr(req, fk, None) or ""
            updates[f"{tool_key}.{fk}"] = val

    if updates:
        await set_settings_map(db, updates)

    logger.info(
        "[SETTINGS] Tool %s %s",
        tool_key,
        "enabled" if req.enabled else "disabled",
    )

    # Invalidate caches whenever the tool config changes
    if tool_key == "tmdb":
        from services.tmdb import invalidate_tmdb_key_cache
        invalidate_tmdb_key_cache()
    if tool_key in ("emby", "plex", "jellyfin"):
        from services.emby import invalidate_emby_config_cache
        invalidate_emby_config_cache()
    return {"success": True, "tool": tool_key, "enabled": req.enabled}


@router.get("/media-source")
async def media_source(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Return the active media source and its connection info."""
    source = await get_active_media_source(db)
    return source or {"source": None}


@router.get("/donation")
async def donation_config(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Operator donation config for the backoffice top-bar heart panel.

    Same shape as the portal ``ui.donation`` block; readable by any
    authenticated backoffice user (the values are shown to every portal
    user anyway)."""
    from services.portal.admin import get_donation_config
    return await get_donation_config(db)


@router.get("/media-folders")
async def get_media_folders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_categories(db)


@router.put("/media-folders")
async def replace_media_folders(
    req: MediaFoldersSaveRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    folders = _validate_media_folder_paths(_normalize_media_folders(req.folders))
    await save_categories(db, folders)
    logger.info("[SETTINGS] saved %s media folders", len(folders))
    return {"success": True, "items": folders}


@router.post("/media-folders")
async def upsert_media_folder(
    req: MediaFolderRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    normalized = _validate_media_folder_paths(_normalize_media_folders([req]))
    if not normalized:
        raise HTTPException(status_code=400, detail="folder_path_required")

    folder = normalized[0]
    categories = await get_categories(db)
    updated = False
    for index, current in enumerate(categories):
        if current.get("key") == folder["key"]:
            categories[index] = folder
            updated = True
            break
    if not updated:
        categories.append(folder)

    await save_categories(db, categories)
    logger.info("[SETTINGS] media folder updated: %s", folder["key"])
    return {"success": True, "item": folder, "items": categories}


@router.get("/tools/{tool_key}/ping")
async def ping_tool(
    tool_key: str,
    db:       AsyncSession = Depends(get_db),
    _:        User         = Depends(get_current_user),
):
    """Check whether a tool's URL is reachable from the backend."""
    if tool_key not in TOOLS_DEFINITION:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_key}'")

    config = await get_tools_config(db)
    cfg    = config.get(tool_key, {})

    if not cfg.get("enabled"):
        return {"online": False, "reason": "disabled"}

    # Special case: OpenSubtitles (no URL, probe via API)
    if tool_key == "opensubtitles":
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            return {"online": False, "reason": "no_api_key"}
        try:
            client = get_external_client()
            resp = await client.get(
                "https://api.opensubtitles.com/api/v1/infos/formats",
                headers={
                    "Api-Key": api_key,
                    "User-Agent": "Mediakeeper v1.0.0",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"online": True, "ok": True, "status": 200}
            return {"online": False, "reason": f"status_{resp.status_code}"}
        except Exception:
            logger.exception("[settings] ping opensubtitles failed")
            return {"online": False, "reason": "tool_ping_failed"}

    # Special case: TMDB (no URL, probe via API)
    if tool_key == "tmdb":
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            return {"online": False, "reason": "no_api_key"}
        try:
            client = get_external_client()
            resp = await client.get(
                "https://api.themoviedb.org/3/configuration",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5.0,
            )
            return {"online": resp.status_code == 200, "ok": resp.status_code == 200, "status": resp.status_code}
        except Exception:
            logger.exception("[settings] ping tmdb failed")
            return {"online": False, "reason": "tool_ping_failed"}

    url = cfg.get("url", "").strip().rstrip("/")
    if not url:
        return {"online": False, "reason": "no_url"}

    try:
        client = get_internal_client()
        resp = await client.get(url, timeout=5.0)
        return {"online": resp.status_code < 500, "ok": resp.status_code < 500, "status": resp.status_code}
    except Exception:
        logger.exception("[settings] ping %s failed", tool_key)
        return {"online": False, "reason": "tool_ping_failed"}


# ── Network settings (image cache, DNS cache) ────────────────────────


class NetworkSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_cache_enabled: bool | None = None
    dns_cache_enabled: bool | None = None
    dns_cache_ttl_seconds: int | None = None


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


@router.get("/network")
async def get_network_settings(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Read the three toggles + TTL backing the Network panel."""
    keys = [
        "network.image_cache_enabled",
        "network.dns_cache_enabled",
        "network.dns_cache_ttl_seconds",
    ]
    values = await get_settings_map(db, keys)
    ttl_raw = values.get("network.dns_cache_ttl_seconds") or ""
    try:
        ttl = int(ttl_raw) if ttl_raw else 300
    except ValueError:
        ttl = 300
    return {
        "image_cache_enabled":
            (values.get("network.image_cache_enabled") or "").lower() == "true",
        "dns_cache_enabled":
            (values.get("network.dns_cache_enabled") or "").lower() == "true",
        "dns_cache_ttl_seconds": ttl,
    }


@router.put("/network")
async def update_network_settings(
    req: NetworkSettingsRequest,
    db:  AsyncSession = Depends(get_db),
    _:   User         = Depends(get_current_user),
):
    """Persist the toggles + propagate the change to the runtime caches.

    ``model_fields_set`` lets the frontend send only the keys it
    actually changed (e.g. flip just one toggle), and the matching
    cache service is refreshed in place so the change takes effect
    on the very next request instead of waiting for the next
    settings poll.
    """
    sent = req.model_fields_set
    updates: dict[str, str] = {}
    if "image_cache_enabled" in sent and req.image_cache_enabled is not None:
        updates["network.image_cache_enabled"] = _bool_str(req.image_cache_enabled)
    if "dns_cache_enabled" in sent and req.dns_cache_enabled is not None:
        updates["network.dns_cache_enabled"] = _bool_str(req.dns_cache_enabled)
    if "dns_cache_ttl_seconds" in sent and req.dns_cache_ttl_seconds is not None:
        ttl = max(1, int(req.dns_cache_ttl_seconds))
        updates["network.dns_cache_ttl_seconds"] = str(ttl)

    if updates:
        await set_settings_map(db, updates)

    # Propagate the change to the live caches so the admin doesn't
    # need to bounce the container.
    if "image_cache_enabled" in sent:
        from services.portal.image_cache import refresh_enabled_flag
        await refresh_enabled_flag(db, force=True)
    if "dns_cache_enabled" in sent or "dns_cache_ttl_seconds" in sent:
        from services.portal.dns_cache import refresh_from_settings as dns_refresh
        await dns_refresh(db)

    return {"success": True}


router.include_router(dashboard_router)
