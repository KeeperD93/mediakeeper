"""Re-resolve playback library names that aren't a real Emby library.

Shared by the manual ``/api/stats/migrate/library-names`` endpoint and the
periodic library-cache refresh, so historical rows stamped with a sub-folder
name (e.g. ``Archives``) heal to the true Emby library (CollectionFolder).
"""
import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import LibraryCache, PlaybackSession
from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.stats.aggregator")


async def repair_library_names(db: AsyncSession, collect_details: bool = False) -> dict:
    """Re-resolve rows whose ``library_name`` is missing or not a real Emby
    library (a sub-folder / slug) to the true CollectionFolder name.

    Idempotent: rows already on a valid library name are skipped, so once the
    collector writes correct names the steady state costs no Emby calls (and a
    fresh install with no history is a no-op).

    Both paths fetch each candidate's ancestry fresh and stamp only rows that map
    to a real library; a raw sub-folder fallback is counted "unresolved" and never
    written (it would persist a wrong slug and never converge). ``collect_details``
    additionally returns a per-row ``details`` list — migrated rows, and unresolved
    rows with the raw ancestry so the admin can see why no library was found.
    """
    from services.stats_collector import (
        _emby_admin_user_id,
        _fetch_ancestors,
        _match_library_name,
        _normalize_library_name,
    )

    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return {"error": "no_active_media_source"}
    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return {"error": "missing_url_or_api_key"}

    # Real Emby library names + the alias map the resolver uses to canonicalise
    # a folder ancestor when no CollectionFolder is found.
    library_rows = (await db.execute(select(LibraryCache.lib_id, LibraryCache.name))).all()
    valid_names = {r.name for r in library_rows if r.name}
    library_aliases = {
        "by_id": {str(r.lib_id): r.name for r in library_rows if r.lib_id and r.name},
        "by_name": {_normalize_library_name(r.name): r.name for r in library_rows if r.name},
    }

    # Target rows whose name is missing or not a known Emby library (sub-folder
    # / slug). Rows already on a real library name are left untouched.
    conds = [PlaybackSession.library_name.is_(None)]
    if valid_names:
        conds.append(PlaybackSession.library_name.notin_(valid_names))
    rows = (await db.execute(select(PlaybackSession).where(or_(*conds)))).scalars().all()

    # Query the ancestry as an Emby user so the virtual CollectionFolder (real
    # library name) is exposed instead of the physical folder slug. Skip the
    # /Users call when there is nothing to repair (steady state / fresh install).
    view_user_id = await _emby_admin_user_id(url, api_key) if rows else None

    migrated = unresolved = errors = 0
    details = [] if collect_details else None
    for row in rows:
        try:
            # Fetch fresh and stamp ONLY rows resolving to a REAL library; a raw
            # sub-folder fallback is counted "unresolved", never written (it would
            # persist a wrong slug and never converge).
            ancestors = await _fetch_ancestors(row.item_id, url, api_key, view_user_id)
            name, resolved = _match_library_name(ancestors or [], library_aliases)
            if resolved and name:
                row.library_name = name
                migrated += 1
                if collect_details:
                    details.append({
                        "item_id": row.item_id,
                        "item_name": row.item_name,
                        "status": "migrated",
                        "library_name": name,
                    })
            else:
                unresolved += 1
                if collect_details:
                    details.append({
                        "item_id": row.item_id,
                        "item_name": row.item_name,
                        "status": "unresolved",
                        "fallback": name,
                        "ancestors": [
                            {"type": a.get("Type"), "name": a.get("Name")}
                            for a in (ancestors or [])
                        ],
                    })
        except Exception:  # noqa: S112 -- best-effort per row, keep repairing the rest
            logger.warning("Library-name repair failed for item %s", row.item_id, exc_info=True)
            errors += 1
            if collect_details:
                details.append({
                    "item_id": row.item_id,
                    "item_name": row.item_name,
                    "status": "error",
                })
    await db.commit()
    if migrated:
        logger.info("Library-name repair: %s re-resolved, %s unresolved", migrated, unresolved)
    result = {
        "candidates": len(rows),
        "migrated": migrated,
        "unresolved": unresolved,
        "errors": errors,
    }
    if collect_details:
        result["details"] = details
    return result
