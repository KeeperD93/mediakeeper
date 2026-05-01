"""Orchestration: iterate over Emby items and apply the TMDB -> IMDB -> search cascade."""
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.settings import get_active_media_source
from services.tmdb import _get_tmdb_key
from services.portal.search_index import refresh_search_availability

from ._index_ops import _upsert_index
from ._match import _coerce_int, _resolve_by_imdb, _resolve_by_search

logger = logging.getLogger("mediakeeper.portal.emby_index")


async def sync_emby_tmdb_index(db: AsyncSession) -> dict:
    """
    Fetch all Emby library items and store their TMDB IDs.

    Each item goes through a 3-step cascade:
      1. Trust ``ProviderIds.Tmdb`` when present.
      2. Resolve via IMDB id using TMDB ``/find``.
      3. Fuzzy search TMDB by title + year.

    Returns a dict with per-stage counters so operators can diagnose
    which matching strategy is doing the heavy lifting.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return {"synced": 0, "skipped": 0, "error": "no_source"}

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return {"synced": 0, "skipped": 0, "error": "no_config"}

    tmdb_key = await _get_tmdb_key(db)

    client = get_internal_client()
    headers = {"X-Emby-Token": api_key}
    counters = {"tmdb": 0, "imdb": 0, "search": 0, "skipped": 0}
    # Track seen ids per media_type so a category that returns zero items
    # (Emby quirk, permission issue) can never trigger a wipe of the
    # other category's index rows.
    seen_by_type: dict[str, set[str]] = {"movie": set(), "tv": set()}
    purge_ok_by_type: dict[str, bool] = {"movie": False, "tv": False}
    PAGE_LIMIT = 10000

    for item_type, media_type in [("Movie", "movie"), ("Series", "tv")]:
        try:
            res = await client.get(
                f"{url}/Items",
                params={
                    "IncludeItemTypes": item_type,
                    "Recursive": "true",
                    "Fields": "ProviderIds,ProductionYear",
                    "Limit": str(PAGE_LIMIT),
                },
                headers=headers,
            )
            if res.status_code != 200:
                logger.warning(f"[EMBY_INDEX] HTTP {res.status_code} for {item_type}")
                continue

            payload = res.json()
            items = payload.get("Items", []) or []
            total = payload.get("TotalRecordCount", len(items))
            # Emby's /Items has a Limit cap. If the real total exceeds
            # what we received, the listing is truncated — purging would
            # delete legitimate items that fell off the page.
            truncated = len(items) < total
            if truncated:
                logger.warning(
                    f"[EMBY_INDEX] {item_type} truncated ({len(items)}/{total}) — skip purge"
                )

            for item in items:
                emby_id = item.get("Id", "")
                if not emby_id:
                    counters["skipped"] += 1
                    continue
                seen_by_type[media_type].add(emby_id)

                name = item.get("Name", "")
                year = item.get("ProductionYear")
                providers = item.get("ProviderIds", {})

                raw_tmdb = providers.get("Tmdb") or providers.get("tmdb")
                tmdb_id_int = _coerce_int(raw_tmdb)
                matched_via = "tmdb" if tmdb_id_int else None

                if not tmdb_id_int:
                    raw_imdb = providers.get("Imdb") or providers.get("imdb")
                    if raw_imdb and tmdb_key:
                        tmdb_id_int = await _resolve_by_imdb(tmdb_key, raw_imdb, media_type)
                        if tmdb_id_int:
                            matched_via = "imdb"

                if not tmdb_id_int and tmdb_key and name:
                    tmdb_id_int = await _resolve_by_search(
                        tmdb_key, media_type, name, year,
                    )
                    if tmdb_id_int:
                        matched_via = "search"

                if not tmdb_id_int:
                    counters["skipped"] += 1
                    logger.debug(f"[EMBY_INDEX] skipped {media_type} '{name}' ({year}) — no match")
                    continue

                await _upsert_index(db, emby_id, tmdb_id_int, media_type, name)
                counters[matched_via] += 1

            # Enable purge only AFTER the whole listing has been walked
            # without exception — a partial scan would leave seen_by_type
            # incomplete and cause valid rows to be deleted as orphans.
            if not truncated and items:
                purge_ok_by_type[media_type] = True

        except Exception as e:
            logger.error(f"[EMBY_INDEX] Error syncing {item_type}: {e}")

    # Purge orphan rows (their Emby item no longer exists) so a
    # re-imported title doesn't leave a dead row that fakes a "partial"
    # availability pill. Strategy:
    #  - scoped per media_type (a quiet category never wipes the other)
    #  - only when the listing was complete and non-empty for that type
    #  - delete by primary key in chunks to dodge SQL IN-clause caps
    purged = 0
    CHUNK = 500
    for mt, can_purge in purge_ok_by_type.items():
        if not can_purge:
            continue
        seen = seen_by_type[mt]
        existing = await db.execute(
            select(EmbyTmdbIndex.id, EmbyTmdbIndex.emby_item_id)
            .where(EmbyTmdbIndex.media_type == mt)
        )
        orphan_ids = [row.id for row in existing if row.emby_item_id not in seen]
        for i in range(0, len(orphan_ids), CHUNK):
            chunk = orphan_ids[i:i + CHUNK]
            res = await db.execute(delete(EmbyTmdbIndex).where(EmbyTmdbIndex.id.in_(chunk)))
            purged += res.rowcount or 0

    await refresh_search_availability(db)
    await db.commit()
    synced = counters["tmdb"] + counters["imdb"] + counters["search"]
    logger.info(
        f"[EMBY_INDEX] Sync done: {synced} synced "
        f"(tmdb={counters['tmdb']}, imdb={counters['imdb']}, search={counters['search']}), "
        f"{counters['skipped']} skipped, {purged} purged"
    )
    return {"synced": synced, "skipped": counters["skipped"], "purged": purged, **counters}
