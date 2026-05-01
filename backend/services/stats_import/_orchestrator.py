"""Orchestration: full Jellystats import + targeted purge."""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from ._activity import _import_playback_activity
from ._blocks import _extract_blocks
from ._enrich import _enrich_usernames, _migrate_library_names
from ._libraries import _build_item_to_library, _import_libraries
from ._plugin import _import_plugin_reporting

logger = logging.getLogger("mediakeeper.stats.import")


async def import_jellystats_backup(db: AsyncSession, data: dict) -> dict:
    """
    Importe un backup Jellystats JSON in les tables Mediakeeper.
    - jf_playback_activity → playback_sessions
    - jf_libraries → library_cache
    Ignore duplicates (based on session_key = Jellystats Id).
    """
    report = {
        "playback_imported": 0,
        "playback_skipped": 0,
        "playback_errors": 0,
        "libraries_imported": 0,
        "libraries_skipped": 0,
    }

    now = datetime.now(timezone.utc)

    jf_libraries = _extract_blocks(data, "jf_libraries")
    await _import_libraries(db, jf_libraries, report, now)

    jf_lib_items = _extract_blocks(data, "jf_library_items")
    jf_lib_episodes = _extract_blocks(data, "jf_library_episodes")
    item_to_library = _build_item_to_library(jf_libraries, jf_lib_items, jf_lib_episodes)

    existing_keys_res = await db.execute(select(PlaybackSession.session_key))
    existing_keys = {r[0] for r in existing_keys_res.all()}

    jf_activity = _extract_blocks(data, "jf_playback_activity")
    await _import_playback_activity(db, jf_activity, existing_keys, item_to_library, report, now)

    jf_plugin = _extract_blocks(data, "jf_playback_reporting_plugin_data")
    await _import_plugin_reporting(db, jf_plugin, existing_keys, item_to_library, report, now)

    jf_users = _extract_blocks(data, "jf_users")
    await _enrich_usernames(db, jf_users)
    await _migrate_library_names(db, item_to_library, report)

    await db.commit()
    logger.info(f"Jellystats import complete: {report}")
    return report


async def purge_jellystats_import(db: AsyncSession) -> dict:
    """
    Delete ONLY the data imported from Jellystats.
    Identified by session_key starting with 'js_' or 'jsplugin_'.
    Does NOT touch the data collected natively by Mediakeeper.
    """
    count_js = await db.execute(
        select(func.count(PlaybackSession.id)).where(
            PlaybackSession.session_key.like("js_%")
        )
    )
    count_plugin = await db.execute(
        select(func.count(PlaybackSession.id)).where(
            PlaybackSession.session_key.like("jsplugin_%")
        )
    )
    total_js = count_js.scalar() or 0
    total_plugin = count_plugin.scalar() or 0

    await db.execute(
        delete(PlaybackSession).where(
            or_(
                PlaybackSession.session_key.like("js_%"),
                PlaybackSession.session_key.like("jsplugin_%"),
            )
        )
    )

    # library_cache is untouched: it is refreshed by the periodic task.
    await db.commit()
    logger.info(f"Jellystats purge: {total_js} playback + {total_plugin} plugin removed")
    return {
        "purged_playback": total_js,
        "purged_plugin": total_plugin,
        "total_purged": total_js + total_plugin,
    }
