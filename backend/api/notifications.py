import json
from copy import deepcopy
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.user import User
from api.auth import get_current_user
from services.discord import send_discord_test, DEFAULT_COLORS, SAMPLE_SYSTEM, get_default_templates, get_tpl_vars
from services.settings import MASKED_SECRET_LENGTH, get_notification_channel, set_notification_channel
from api.notifications_history import router as history_router

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class DiscordTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_url: str = ""
    webhook_id:  str | None = None
    wh_config:   dict = Field(default_factory=dict)   # full webhook config
    test_type:   str = "movie"


class DiscordEvents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    added: bool = False
    offline: bool = False
    duplicate: bool = False
    new_request: bool = False
    request_approved: bool = False
    request_available: bool = False
    request_rejected: bool = False
    new_issue: bool = False
    issue_comment: bool = False
    issue_resolved: bool = False
    partially_available: bool = False
    emby_alerts: bool = False


class WebhookItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    url: str
    url_configured: bool = False
    enabled: bool = True
    events: DiscordEvents = Field(default_factory=DiscordEvents)
    templates: dict = Field(default_factory=dict)    # tpl_key -> template text
    settings:  dict = Field(default_factory=dict)    # tpl_key -> {color, image_style}
    image_host: str = "emby"                         # "emby" | "imgur"


class DiscordConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    delay: int = 10
    image_host: str = "emby"
    webhooks: list[WebhookItem] = Field(default_factory=list)
    # Set true to acknowledge wiping every previously-saved webhook.
    # The server refuses an empty webhook list otherwise to prevent a
    # partially-filled form from silently destroying the encrypted URLs.
    confirm_clear: bool = False


class ImgurConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = ""
    client_secret: str = ""
    client_secret_configured: bool = False
    client_secret_length: int = 0
    # Same opt-in clear acknowledgement as DiscordConfig — a blank
    # client_secret with client_secret_configured=False would otherwise
    # wipe the encrypted secret stored in the database.
    confirm_clear: bool = False


def _load_channel_json(raw: str, default: dict) -> dict:
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    return deepcopy(default)


def _mask_discord_config(data: dict) -> dict:
    masked = deepcopy(data)
    masked["webhooks"] = [
        {
            **webhook,
            "url": "",
            "url_configured": bool((webhook.get("url") or "").strip()),
        }
        for webhook in masked.get("webhooks", [])
    ]
    return masked


def _merge_discord_config(existing: dict, incoming: dict) -> dict:
    merged = deepcopy(incoming)
    merged.pop("confirm_clear", None)
    existing_by_id = {
        str(webhook.get("id")): webhook
        for webhook in existing.get("webhooks", [])
        if webhook.get("id")
    }

    webhooks: list[dict] = []
    for webhook in merged.get("webhooks", []):
        item = deepcopy(webhook)
        current = existing_by_id.get(str(item.get("id")))
        url = (item.get("url") or "").strip()
        if not url and item.get("url_configured") and current and current.get("url"):
            item["url"] = current["url"]
        else:
            item["url"] = url
        item.pop("url_configured", None)
        webhooks.append(item)

    merged["webhooks"] = webhooks
    return merged


def _mask_imgur_config(data: dict) -> dict:
    masked = deepcopy(data)
    secret = (masked.get("client_secret") or "").strip()
    masked["client_secret_configured"] = bool(secret)
    masked["client_secret_length"] = MASKED_SECRET_LENGTH if secret else 0
    masked["client_secret"] = ""
    return masked


def _merge_imgur_config(existing: dict, incoming: dict) -> dict:
    merged = deepcopy(incoming)
    merged.pop("confirm_clear", None)
    secret = (merged.get("client_secret") or "").strip()
    if not secret and merged.get("client_secret_configured") and existing.get("client_secret"):
        merged["client_secret"] = existing["client_secret"]
    else:
        merged["client_secret"] = secret
    merged.pop("client_secret_configured", None)
    merged.pop("client_secret_length", None)
    return merged


def _assert_clear_acknowledged(
    existing: dict,
    merged: dict,
    *,
    sensitive_fields: tuple[str, ...],
    confirm_clear: bool,
    detail: str,
) -> None:
    """Refuse a save that would wipe a previously-set sensitive value
    unless the caller explicitly acknowledged the clear.

    Truthy comparison covers both list shapes (Discord ``webhooks``)
    and scalar shapes (Imgur ``client_secret``).
    """
    if confirm_clear:
        return
    for field in sensitive_fields:
        if bool(existing.get(field)) and not bool(merged.get(field)):
            raise HTTPException(status_code=409, detail=detail)


@router.post("/discord/test")
async def test_discord(
    req: DiscordTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Send a one-off test Discord message."""
    webhook_url = (req.webhook_url or "").strip()
    if not webhook_url and req.webhook_id:
        current = _load_channel_json(await get_notification_channel(db, "discord"), DiscordConfig().model_dump())
        for webhook in current.get("webhooks", []):
            if str(webhook.get("id")) == str(req.webhook_id):
                webhook_url = (webhook.get("url") or "").strip()
                break
    return await send_discord_test(webhook_url, req.wh_config, req.test_type, db)


@router.get("/discord/meta")
async def get_discord_meta(lang: str = "fr", _: User = Depends(get_current_user)):
    """Return the variables available per template plus defaults and colors."""
    tpl_vars = get_tpl_vars(lang)
    defaults = get_default_templates(lang)
    return {
        "vars":     {k: [{"key": var[0], "desc": var[1]} for var in vars_list] for k, vars_list in tpl_vars.items()},
        "defaults": defaults,
        "colors":   DEFAULT_COLORS,
        "sample_system": list(SAMPLE_SYSTEM.keys()),
    }


@router.get("/discord/config")
async def get_discord_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Load the Discord config from the DB."""
    cfg = DiscordConfig()
    default = cfg.model_dump()
    stored = _load_channel_json(await get_notification_channel(db, "discord"), default)
    return _mask_discord_config(stored)


@router.post("/discord/config")
async def save_discord_config(
    req: DiscordConfig,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Persist the Discord config."""
    default = DiscordConfig().model_dump()
    existing = _load_channel_json(await get_notification_channel(db, "discord"), default)
    incoming = req.model_dump()
    confirm_clear = bool(incoming.get("confirm_clear"))
    merged = _merge_discord_config(existing, incoming)
    _assert_clear_acknowledged(
        existing, merged,
        sensitive_fields=("webhooks",),
        confirm_clear=confirm_clear,
        detail="discord_config_empty_webhooks_requires_confirm_clear",
    )
    await set_notification_channel(db, "discord", json.dumps(merged))
    return {"success": True}


@router.get("/imgur/config")
async def get_imgur_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Load the Imgur config from the DB."""
    cfg = ImgurConfig()
    default = cfg.model_dump()
    stored = _load_channel_json(await get_notification_channel(db, "imgur"), default)
    return _mask_imgur_config(stored)


@router.post("/imgur/config")
async def save_imgur_config(
    req: ImgurConfig,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Persist the Imgur config."""
    default = ImgurConfig().model_dump()
    existing = _load_channel_json(await get_notification_channel(db, "imgur"), default)
    incoming = req.model_dump()
    confirm_clear = bool(incoming.get("confirm_clear"))
    merged = _merge_imgur_config(existing, incoming)
    _assert_clear_acknowledged(
        existing, merged,
        sensitive_fields=("client_secret",),
        confirm_clear=confirm_clear,
        detail="imgur_config_empty_secret_requires_confirm_clear",
    )
    await set_notification_channel(db, "imgur", json.dumps(merged))
    return {"success": True}


# Mount history + rules endpoints under /api/notifications/(history|rules)
router.include_router(history_router)
