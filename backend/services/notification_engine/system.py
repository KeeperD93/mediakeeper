"""Notifications system : offline, duplicate, request, issue, emby_alert."""
import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.discord import build_system_payload, send_discord_webhook
from services.settings import get_notification_channel

from ._common import EVENT_TO_TPL, _is_dnd
from ._log_writer import log_failed, log_sent

logger = logging.getLogger("mediakeeper.notifications")


async def send_system_notification(
    db: AsyncSession,
    event_key: str,
    vars_dict: dict,
):
    """
    Envoie une notification system (offline, duplicate, request, issue, emby_alert).
    event_key → matches the event configured in the webhook AND the template key.
    vars_dict → context variables to inject into the template.
    """
    tpl_key = EVENT_TO_TPL.get(event_key, event_key)

    try:
        raw_config = await get_notification_channel(db, "discord")
        if not raw_config:
            return
        config = json.loads(raw_config)
        if not config.get("enabled"):
            return

        raw_rules = await get_notification_channel(db, "notif_rules")
        rules = {}
        if raw_rules:
            try:
                rules = json.loads(raw_rules)
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass
        if _is_dnd(rules):
            logger.info("[NOTIFICATIONS] DND — notification %s blocked", event_key)
            return

        for wh in config.get("webhooks", []):
            if not wh.get("enabled", True):
                continue
            if not wh.get("events", {}).get(event_key):
                continue
            title = vars_dict.get("title", vars_dict.get("name", ""))
            webhook_name = wh.get("name", "")
            try:
                payload = await build_system_payload(tpl_key, vars_dict, wh, db=db)
                sent = await send_discord_webhook(wh.get("url"), payload)
                if sent:
                    await log_sent(
                        db,
                        event_type=event_key,
                        webhook_name=webhook_name,
                        title=title,
                        message=tpl_key,
                    )
                else:
                    logger.warning("[NOTIFICATIONS] Discord rejected system delivery for %s", event_key)
                    await log_failed(
                        db,
                        event_type=event_key,
                        webhook_name=webhook_name,
                        title=title,
                        message=tpl_key,
                        error="discord_rejected",
                    )
            except Exception as e:
                logger.error("[NOTIFICATIONS] send_system_notification(%s): %s", event_key, e)
                await log_failed(
                    db,
                    event_type=event_key,
                    webhook_name=webhook_name,
                    title=title,
                    message=tpl_key,
                    error=str(e),
                )
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error("[NOTIFICATIONS] send_system_notification error: %s", e, exc_info=True)
