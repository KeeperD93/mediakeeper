"""Bug/suggestion feedback: config + relay to a configured Discord webhook.

Cycle 1: an admin sets a Discord webhook ("link code") + a pseudo, then reports
are relayed straight to that webhook, pre-formatted as the tracker's
``=== BUG === … === END ===`` import block. No storage — pure relay.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from services.discord import send_discord_webhook
from services.settings import get_settings_map, set_settings_map

# The ``.webhook_url`` suffix makes core.encryption treat the value as
# sensitive → encrypted at rest transparently by the _kv layer.
KEY_ENABLED = "bug_report.enabled"
KEY_PSEUDO = "bug_report.discord_pseudo"
KEY_WEBHOOK = "bug_report.webhook_url"
_CONFIG_KEYS = [KEY_ENABLED, KEY_PSEUDO, KEY_WEBHOOK]

PLATFORMS = ("both", "desktop", "mobile")
# Discord caps a webhook message at 2000 chars; the block is wrapped in a
# ``` fence (8 chars), so the block itself must stay under this.
_MAX_BLOCK = 1990


async def get_feedback_config(db: AsyncSession) -> dict:
    v = await get_settings_map(db, _CONFIG_KEYS)
    return {
        "enabled": v.get(KEY_ENABLED) == "true",
        "discord_pseudo": v.get(KEY_PSEUDO, ""),
        "webhook_url": v.get(KEY_WEBHOOK, ""),
    }


async def save_feedback_config(
    db: AsyncSession,
    *,
    enabled: bool | None = None,
    discord_pseudo: str | None = None,
    webhook_url: str | None = None,
) -> None:
    updates: dict[str, str] = {}
    if enabled is not None:
        updates[KEY_ENABLED] = "true" if enabled else "false"
    if discord_pseudo is not None:
        updates[KEY_PSEUDO] = discord_pseudo.strip()[:100]
    if webhook_url is not None:
        updates[KEY_WEBHOOK] = webhook_url.strip()
    if updates:
        await set_settings_map(db, updates)


def _defuse(value: str) -> str:
    """Break any ``===`` run so user text can't forge block delimiters/fields."""
    return (value or "").replace("===", "= = =")


def _oneline(value: str) -> str:
    """Single-line field: defuse delimiters + collapse newlines."""
    return _defuse(value).replace("\r", " ").replace("\n", " ").strip()


def build_report_block(fields: dict, pseudo: str) -> str:
    """Render the tracker-parsable block. ``pseudo`` empty ⇒ anonymous."""
    from api.changelog import APP_VERSION  # lazy: avoids an api→services cycle

    platform = fields.get("platform")
    if platform not in PLATFORMS:
        platform = "both"
    head = (
        "=== BUG ===\n"
        f"TITRE: {_oneline(fields.get('title', ''))}\n"
        f"ZONE: {_oneline(fields.get('zone', '')) or '-'}\n"
        f"MODULE: {_oneline(fields.get('module', '')) or '-'}\n"
        f"ONGLET: {_oneline(fields.get('tab', '')) or '-'}\n"
        f"PLATEFORME: {platform}\n"
        "DESCRIPTION:\n"
    )

    extras: list[str] = []
    repro = _defuse(fields.get("reproduction", "")).strip()
    if repro:
        extras.append(f"Reproduction: {repro}")
    resolution = _oneline(fields.get("resolution", ""))
    if resolution:
        extras.append(f"Résolution: {resolution}")
    kind = "Suggestion" if fields.get("type") == "suggestion" else "Bug"
    tags = [s for s in (_oneline(t)[:30] for t in fields.get("tags", [])) if s]
    extras.append(f"Type: {kind}" + (f" · Étiquettes: {', '.join(tags)}" if tags else ""))
    who = pseudo.strip() if pseudo and pseudo.strip() else "Anonyme"
    extras.append(f"Signalé par: {who} · MediaKeeper {APP_VERSION}")
    tail = "\n\n" + "\n".join(extras) + "\n=== END ==="

    description = _defuse(fields.get("description", "")).strip()
    budget = _MAX_BLOCK - len(head) - len(tail)
    if len(description) > budget:
        description = description[: max(0, budget - 1)].rstrip() + "…"
    return head + description + tail


async def send_feedback_report(db: AsyncSession, fields: dict) -> bool:
    cfg = await get_feedback_config(db)
    if not cfg["enabled"] or not cfg["webhook_url"]:
        return False
    pseudo = "" if fields.get("anonymous") else cfg["discord_pseudo"]
    payload = {
        "username": "MediaKeeper",
        "content": f"```\n{build_report_block(fields, pseudo)}\n```",
        "allowed_mentions": {"parse": []},  # never resolve @everyone/@here/@user
        "flags": 4,                          # SUPPRESS_EMBEDS: no link/image preview
    }
    return await send_discord_webhook(cfg["webhook_url"], payload)


async def send_feedback_handshake(webhook_url: str) -> bool:
    """Test ping the maintainer watches for when a contributor links up."""
    payload = {
        "username": "MediaKeeper",
        "content": "MediaKeeper — liaison feedback confirmée.",
        "allowed_mentions": {"parse": []},
    }
    return await send_discord_webhook(webhook_url, payload)


async def create_pending_report(
    db: AsyncSession,
    *,
    reporter_user_id: int | None,
    reporter_name: str | None,
    fields: dict,
) -> None:
    """Store a delegated portal user's report as ``pending`` for admin review."""
    from models.portal.feedback_report import FeedbackReport  # lazy: avoid cycles

    platform = fields.get("platform")
    if platform not in PLATFORMS:
        platform = "both"
    db.add(
        FeedbackReport(
            reporter_user_id=reporter_user_id,
            reporter_name=(reporter_name or "").strip()[:100] or None,
            type="suggestion" if fields.get("type") == "suggestion" else "bug",
            title=(fields.get("title") or "")[:200],
            description=fields.get("description") or "",
            reproduction=(fields.get("reproduction") or "").strip() or None,
            zone=(fields.get("zone") or "").strip() or None,
            module=(fields.get("module") or "").strip() or None,
            tab=(fields.get("tab") or "").strip() or None,
            platform=platform,
            resolution=(fields.get("resolution") or "").strip() or None,
            tags=[str(t)[:30] for t in (fields.get("tags") or [])][:12],
            anonymous=bool(fields.get("anonymous")),
            status="pending",
        )
    )
    await db.commit()
