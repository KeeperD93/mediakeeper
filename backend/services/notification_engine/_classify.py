"""Promote a synthetic ``Grouped`` notification to ``Series`` or ``Season``.

The notification engine groups several episodes of the same season into a
single Discord card (``Type="Grouped"``). When the batch actually
represents a brand-new series landing in the library, or a complete
season being filled in one shot, we want to fire the dedicated
``added_series`` / ``added_season`` Discord template instead of the
generic grouped one. This module owns that contextual upgrade.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.emby import fetch_item_by_id
from services.watchlist_scanner._emby import _get_emby_episodes

logger = logging.getLogger("mediakeeper.notifications.classify")


async def promote_grouped_items(items: list[dict], db: AsyncSession) -> None:
    """Upgrade each ``Grouped`` item to ``Series``/``Season`` when the
    Emby state shows the batch is more than just episode fill-in."""
    for item in items:
        if item.get("Type") != "Grouped":
            continue
        try:
            new_type = await classify_grouped(item, db)
        except Exception as exc:
            logger.warning("[NOTIFICATIONS] classify failed: %s", exc)
            continue
        if new_type == "Grouped":
            continue
        item["Type"] = new_type
        await enrich_promoted_item(item, db)

# A grouped batch is promoted to ``Season`` only when it carries at least
# this many episodes — guards against single-episode "groups" or 2-pilot
# specials being mis-classified as a complete-season delivery.
MIN_EPISODES_FOR_SEASON = 2


async def classify_grouped(item: dict, db: AsyncSession) -> str:
    """Return the Discord ``Type`` to use for ``item``.

    Returns one of ``"Series"``, ``"Season"`` or ``"Grouped"`` — falls
    back to ``"Grouped"`` whenever Emby cannot be queried or the data
    is ambiguous.

    Promotion rules (asymmetric with auto-fulfill — see request module):
      - All episodes Emby holds for this series come from the batch
        → ``"Series"`` (the show is brand new in the library).
      - All episodes Emby holds for this season come from the batch
        and the batch is wide enough → ``"Season"``.
      - Otherwise → ``"Grouped"`` (default, unchanged behaviour).
    """
    series_id = item.get("SeriesId")
    if not series_id:
        return "Grouped"

    try:
        batch_size = int(item.get("ChildCount") or 0)
    except (TypeError, ValueError):
        return "Grouped"

    if batch_size <= 0:
        return "Grouped"

    eps_in_emby = await _get_emby_episodes(db, str(series_id))
    if not eps_in_emby:
        return "Grouped"

    if len(eps_in_emby) == batch_size:
        return "Series"

    season_num = item.get("IndexNumber")
    if season_num is not None:
        try:
            season_num_int = int(season_num)
        except (TypeError, ValueError):
            return "Grouped"
        season_eps = sum(1 for s, _ in eps_in_emby if s == season_num_int)
        if season_eps == batch_size and batch_size >= MIN_EPISODES_FOR_SEASON:
            return "Season"

    return "Grouped"


async def enrich_promoted_item(item: dict, db: AsyncSession) -> None:
    """Mutate ``item`` in place so the Discord renderer has the data it
    needs once the batch has been promoted to ``Series``/``Season``.

    The synthetic ``Grouped`` payload built upstream carries an English
    placeholder in ``Overview`` ("A batch of N new episodes…"); for a
    promoted item we want the real series-level synopsis so the
    ``<synopsis>`` template variable resolves to something meaningful.
    The series details are also the canonical source for genres, year
    and provider IDs that the Discord card surfaces.
    """
    series_id = item.get("SeriesId")
    if not series_id:
        return
    try:
        details = await fetch_item_by_id(db, str(series_id))
    except Exception as exc:
        logger.warning("[NOTIFICATIONS] series enrich failed: %s", exc)
        return
    if not details:
        return

    item["Overview"] = details.get("Overview") or ""
    if details.get("ProductionYear"):
        item["ProductionYear"] = details["ProductionYear"]
    if details.get("PremiereDate"):
        item.setdefault("PremiereDate", details["PremiereDate"])
    series_providers = details.get("ProviderIds") or {}
    if series_providers:
        item["ProviderIds"] = series_providers
    if details.get("Genres"):
        item["Genres"] = details["Genres"]
