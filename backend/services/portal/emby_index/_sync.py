"""Orchestration: iterate over Emby items and apply the TMDB -> IMDB -> search cascade."""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.settings import get_active_media_source
from services.tmdb import _get_tmdb_key, get_media_details

from ._index_ops import _upsert_index
from ._match import _coerce_int, _resolve_by_imdb, _resolve_by_search

logger = logging.getLogger("mediakeeper.portal.emby_index")


def _parse_emby_date_created(value: object) -> datetime | None:
    """Best-effort parse of Emby's ``DateCreated`` payload.

    Emby commonly emits ``2023-04-12T18:30:00.0000000Z`` but a handful of
    builds drop the trailing ``Z`` or replace it with ``+00:00``; some
    older installs even return naive timestamps. We accept all three
    flavours and always return a tz-aware UTC ``datetime`` (or ``None``
    when the input is unusable). The raw value is surfaced in DEBUG
    logs only so a misformatted payload never blocks a sync run.
    """
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Python's ISO parser tolerates fractional seconds up to 6 digits;
    # Emby occasionally pads to 7 ("ticks"). Trim the excess so .NET's
    # extra precision doesn't trip the parse.
    if "." in text:
        head, _, tail = text.partition(".")
        frac = tail
        offset = ""
        for sep in ("+", "-"):
            idx = tail.find(sep, 1)
            if idx >= 0:
                frac = tail[:idx]
                offset = tail[idx:]
                break
        if len(frac) > 6:
            frac = frac[:6]
        text = f"{head}.{frac}{offset}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# Cap TMDB language fetches per sync run. The enrichment is best-effort
# — anything the cap defers will be picked up next time the sync is
# triggered. Keeps a fresh install from blasting hundreds of requests
# at TMDB on the first crawl.
MAX_TMDB_LANG_FETCHES_PER_SYNC = 250


async def sync_emby_tmdb_index(db: AsyncSession, *, recent_limit: int | None = None) -> dict:
    """
    Fetch Emby library items and store their TMDB IDs.

    Each item goes through a 3-step cascade:
      1. Trust ``ProviderIds.Tmdb`` when present.
      2. Resolve via IMDB id using TMDB ``/find``.
      3. Fuzzy search TMDB by title + year.

    ``recent_limit`` switches to the cheap "recently added" mode: only the N
    newest items per type are fetched (``SortBy=DateCreated``) and neither the
    orphan purge nor the language enrichment runs — both need the full library
    view. Meant to run every few minutes so freshly-added content shows up
    fast; the periodic full scan handles removals and enrichment.

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
    counters = {"tmdb": 0, "imdb": 0, "search": 0, "skipped": 0, "lang_enriched": 0}
    # Track seen ids per media_type so a category that returns zero items
    # (Emby quirk, permission issue) can never trigger a wipe of the
    # other category's index rows.
    seen_by_type: dict[str, set[str]] = {"movie": set(), "tv": set()}
    purge_ok_by_type: dict[str, bool] = {"movie": False, "tv": False}
    PAGE_LIMIT = 10000

    for item_type, media_type in [("Movie", "movie"), ("Series", "tv")]:
        try:
            params = {
                "IncludeItemTypes": item_type,
                "Recursive": "true",
                "Fields": "ProviderIds,ProductionYear,DateCreated",
                "Limit": str(recent_limit or PAGE_LIMIT),
            }
            if recent_limit:
                params["SortBy"] = "DateCreated"
                params["SortOrder"] = "Descending"
            res = await client.get(f"{url}/Items", params=params, headers=headers)
            if res.status_code != 200:
                logger.warning("[EMBY_INDEX] HTTP %s for %s", res.status_code, item_type)
                continue

            payload = res.json()
            items = payload.get("Items", []) or []
            total = payload.get("TotalRecordCount", len(items))
            # Emby's /Items has a Limit cap. If the real total exceeds
            # what we received, the listing is truncated — purging would
            # delete legitimate items that fell off the page.
            # Recent mode fetches a small window on purpose, so the truncation
            # check (and the purge it guards) is full-scan only.
            truncated = recent_limit is None and len(items) < total
            if truncated:
                logger.warning(
                    "[EMBY_INDEX] %s truncated (%s/%s) — skip purge",
                    item_type, len(items), total,
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
                    logger.debug("[EMBY_INDEX] skipped %s '%s' (%s) — no match", media_type, name, year)
                    continue

                date_created = _parse_emby_date_created(item.get("DateCreated"))
                await _upsert_index(
                    db, emby_id, tmdb_id_int, media_type, name,
                    production_year=year if isinstance(year, int) else None,
                    date_created=date_created,
                )
                counters[matched_via] += 1

            # Enable purge only AFTER the whole listing has been walked
            # without exception — a partial scan would leave seen_by_type
            # incomplete and cause valid rows to be deleted as orphans.
            if recent_limit is None and not truncated and items:
                purge_ok_by_type[media_type] = True

        except Exception as e:
            logger.error("[EMBY_INDEX] Error syncing %s: %s", item_type, e)

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

    # ── Lazy enrichment: original_language from TMDB ────────────────────
    # Only rows with a resolved tmdb_id but no cached language yet.
    # Capped per-run to keep the sync bounded; remaining rows resume next time.
    if recent_limit is None and tmdb_key:
        missing = (await db.execute(
            select(EmbyTmdbIndex.id, EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type)
            .where(EmbyTmdbIndex.original_language.is_(None))
            .limit(MAX_TMDB_LANG_FETCHES_PER_SYNC + 1)
        )).all()
        cap_hit = len(missing) > MAX_TMDB_LANG_FETCHES_PER_SYNC
        for row in missing[:MAX_TMDB_LANG_FETCHES_PER_SYNC]:
            try:
                details = await get_media_details(db, row.tmdb_id, row.media_type)
            except Exception as e:  # noqa: S110 -- best-effort; never block sync on TMDB
                logger.debug(
                    "[EMBY_INDEX] lang fetch failed for %s/%s: %s",
                    row.media_type, row.tmdb_id, e,
                )
                continue
            if not details:
                continue
            lang = details.get("original_language")
            if not lang:
                continue
            await db.execute(
                EmbyTmdbIndex.__table__.update()
                .where(
                    EmbyTmdbIndex.id == row.id,
                    EmbyTmdbIndex.original_language.is_(None),
                )
                .values(original_language=lang[:2].lower())
            )
            counters["lang_enriched"] += 1
        if cap_hit:
            logger.warning(
                "[EMBY_INDEX] TMDB lang enrichment hit cap (%s); remaining rows resume next sync",
                MAX_TMDB_LANG_FETCHES_PER_SYNC,
            )

    await db.commit()
    synced = counters["tmdb"] + counters["imdb"] + counters["search"]
    mode = "Recent sync" if recent_limit else "Sync"
    logger.info(
        "[EMBY_INDEX] %s done: %s synced (tmdb=%s, imdb=%s, search=%s), "
        "%s skipped, %s purged, lang_enriched=%s",
        mode, synced, counters["tmdb"], counters["imdb"], counters["search"],
        counters["skipped"], purged, counters["lang_enriched"],
    )
    return {"synced": synced, "skipped": counters["skipped"], "purged": purged, **counters}
