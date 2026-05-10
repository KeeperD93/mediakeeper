"""Detection des new ajouts Emby + file queue + grouping + envoi."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import engine
from services.discord import build_discord_payload, send_discord_webhook
from services.emby import _get_emby_config, fetch_item_by_id, get_latest_items
from services.settings import (
    get_notification_channel,
    get_setting,
    set_notification_channel,
    set_setting,
)

from ._classify import promote_grouped_items
from ._common import _is_dnd, _parse_date
from ._log_writer import log_failed, log_sent
from ._request_fulfill import try_auto_fulfill

logger = logging.getLogger("mediakeeper.notifications")

# Quand Emby crée un item juste après le scan, ses metadata (Overview,
# ProductionYear, ProviderIds…) sont enrichies en arrière-plan et peuvent
# arriver quelques secondes après. On re-fetch l'item à chaque tick et on
# diffère la notif tant qu'elle est incomplète, dans la limite ci-dessous
# pour ne pas la perdre indéfiniment si Emby n'enrichit jamais (rare cas
# de fichier sans correspondance TMDB).
MAX_FETCH_RETRIES = 5


async def check_and_send_notifications():
    """Point d'entry du scheduler — called all les 60s."""
    try:
        async with AsyncSession(engine) as db:
            await _process_notifications(db)
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error moteur: {e}", exc_info=True)


async def _load_discord_config(db: AsyncSession):
    raw_config = await get_notification_channel(db, "discord")
    if not raw_config:
        return None
    try:
        config = json.loads(raw_config)
    except Exception:
        logger.error("[NOTIFICATIONS] Config Discord corrompue")
        return None
    if not config.get("enabled"):
        return None
    if not config.get("webhooks"):
        return None
    return config


async def _load_imgur_creds(db: AsyncSession) -> tuple[str, str]:
    raw_imgur = await get_notification_channel(db, "imgur")
    if not raw_imgur:
        return "", ""
    try:
        data = json.loads(raw_imgur)
        return data.get("client_id", ""), data.get("client_secret", "")
    except Exception:
        return "", ""


async def _load_rules(db: AsyncSession) -> dict:
    raw_rules = await get_notification_channel(db, "notif_rules")
    if not raw_rules:
        return {}
    try:
        return json.loads(raw_rules)
    except Exception:
        return {}


async def _detect_new_items(db: AsyncSession, now: datetime) -> list[dict]:
    """Compare DateCreated Emby with le last pointer saved."""
    last_date_str = await get_setting(db, "notifications.last_emby_date")
    if not last_date_str:
        await set_setting(db, "notifications.last_emby_date", now.isoformat())
        return []

    last_dt = _parse_date(last_date_str)
    if not last_dt:
        await set_setting(db, "notifications.last_emby_date", now.isoformat())
        return []

    items = await get_latest_items(db, limit=50)
    new_items: list[dict] = []
    max_dt = last_dt

    for item in items or []:
        item_dt = _parse_date(item.get("DateCreated"))
        if not item_dt:
            continue
        if item_dt > last_dt:
            new_items.append(item)
            if item_dt > max_dt:
                max_dt = item_dt

    if max_dt > last_dt:
        await set_setting(db, "notifications.last_emby_date", max_dt.isoformat())
    return new_items


def _is_item_metadata_complete(item: dict) -> bool:
    """Heuristique pour décider si Emby a fini d'enrichir l'item.

    Pour un film, on attend Overview ET (ProductionYear OU PremiereDate)
    car ce sont les deux blocs principaux du payload Discord. Pour un
    épisode, l'Overview suffit — la série est déjà indexée et fournit le
    reste.
    """
    if not item.get("Overview"):
        return False
    if item.get("Type") == "Episode":
        return True
    return bool(item.get("ProductionYear")) or bool(item.get("PremiereDate"))


def _group_episodes(ready_items: list[dict]) -> list[dict]:
    """>=2 episodes of the same season -> 1 'Grouped' notification."""
    grouped_episodes: dict[str, list[dict]] = {}
    final_notifications: list[dict] = []

    for item in ready_items:
        if item.get("Type") == "Episode":
            series_id = item.get("SeriesId")
            season    = item.get("ParentIndexNumber")
            if series_id and season is not None:
                key = f"{series_id}_{season}"
                grouped_episodes.setdefault(key, []).append(item)
                continue
        final_notifications.append(item)

    for group in grouped_episodes.values():
        if len(group) >= 2:
            first = group[0]
            s_num = first.get("ParentIndexNumber", 0)
            nb_ep = len(group)
            synthetic = {
                "Type":             "Grouped",
                "Name":             first.get("SeriesName", ""),
                "SeriesName":       first.get("SeriesName", ""),
                "IndexNumber":      s_num,
                "ProductionYear":   first.get("ProductionYear", ""),
                "SeriesId":         first.get("SeriesId"),
                "Id":               first.get("SeriesId"),
                "ChildCount":       nb_ep,
                "ProviderIds":      first.get("SeriesProviderIds", {}),
                "Overview":         f"A batch of {nb_ep} new episodes has been added for season {s_num} of {first.get('SeriesName', '')}.",
            }
            final_notifications.append(synthetic)
            logger.info(f"[NOTIFICATIONS] Grouping {nb_ep} episodes → 1 notification Season")
        else:
            final_notifications.extend(group)

    return final_notifications


async def _send_item(db, item, webhooks, emby_url, emby_api_key, imgur_id, imgur_secret):
    """Send an item to every webhook enabled for 'added'."""
    for wh in webhooks:
        if not wh.get("enabled", True):
            continue
        if not wh.get("events", {}).get("added"):
            continue
        item_type = item.get("Type", "Movie")
        event_type = f"added_{item_type.lower()}"
        webhook_name = wh.get("name", "")
        title = item.get("SeriesName") or item.get("Name", "")
        try:
            payload = await build_discord_payload(
                item, wh, emby_url, emby_api_key, imgur_id, imgur_secret, db=db,
            )
            sent = await send_discord_webhook(wh.get("url"), payload)
            if sent:
                await log_sent(
                    db,
                    event_type=event_type,
                    webhook_name=webhook_name,
                    title=title,
                    message=item.get("Name", ""),
                )
                logger.info(f"[NOTIFICATIONS] History saved: {title} ({item_type})")
            else:
                logger.warning(f"[NOTIFICATIONS] Discord rejected delivery for {title} ({item_type})")
                await log_failed(
                    db,
                    event_type=event_type,
                    webhook_name=webhook_name,
                    title=title,
                    message=item.get("Name", ""),
                    error="discord_rejected",
                )
        except Exception as e:
            logger.error(f"[NOTIFICATIONS] Error envoi: {e}")
            await log_failed(
                db,
                event_type=event_type,
                webhook_name=webhook_name,
                title=item.get("Name", ""),
                message="",
                error=str(e),
            )
        await asyncio.sleep(0.5)


async def _process_notifications(db: AsyncSession):
    config = await _load_discord_config(db)
    if not config:
        return
    webhooks = config.get("webhooks", [])

    emby_cfg = await _get_emby_config(db)
    if not emby_cfg:
        return
    emby_url, emby_api_key = emby_cfg

    imgur_id, imgur_secret = await _load_imgur_creds(db)
    rules = await _load_rules(db)

    now = datetime.now(timezone.utc)
    new_items = await _detect_new_items(db, now)

    queue_str = await get_notification_channel(db, "queue")
    queue = json.loads(queue_str) if queue_str else []

    for item in new_items:
        queue.append({"queued_at": now.timestamp(), "item": item, "retries": 0})

    if new_items:
        logger.info(f"[NOTIFICATIONS] {len(new_items)} new media en file queue")

    delay_seconds = max(0, int(config.get("delay", 10)))
    ready_items: list[dict] = []
    ready_queue_entries: list[dict] = []
    remaining_queue: list[dict] = []

    for q in queue:
        if now.timestamp() - q["queued_at"] < delay_seconds:
            remaining_queue.append(q)
            continue

        item = q["item"]
        retries = q.get("retries", 0)

        # Re-fetch pour récupérer la version Emby la plus à jour (Emby
        # finit souvent d'enrichir après notre première détection).
        fresh = await fetch_item_by_id(db, item.get("Id"))
        if fresh:
            item = fresh

        if _is_item_metadata_complete(item) or retries >= MAX_FETCH_RETRIES:
            if not _is_item_metadata_complete(item):
                logger.warning(
                    f"[NOTIFICATIONS] {item.get('Name')} sent with incomplete metadata after {retries} retries"
                )
            ready_items.append(item)
            ready_queue_entries.append({**q, "item": item})
        else:
            logger.info(
                f"[NOTIFICATIONS] {item.get('Name')} metadata incomplete — defer (retry {retries + 1}/{MAX_FETCH_RETRIES})"
            )
            remaining_queue.append({**q, "item": item, "retries": retries + 1})

    final_notifications = _group_episodes(ready_items)
    await promote_grouped_items(final_notifications, db)

    for item in final_notifications:
        try:
            await try_auto_fulfill(item, db)
        except Exception as exc:
            # Auto-fulfill is a side-effect of the notif scan — a failure
            # here must never abort the Discord delivery loop.
            logger.error(f"[NOTIFICATIONS] auto-fulfill error: {exc}")

    if _is_dnd(rules):
        logger.info("[NOTIFICATIONS] DND active — media additions not sent")
        remaining_queue.extend(ready_queue_entries)
    else:
        for item in final_notifications:
            await _send_item(db, item, webhooks, emby_url, emby_api_key, imgur_id, imgur_secret)

    await db.commit()
    await set_notification_channel(db, "queue", json.dumps(remaining_queue))
