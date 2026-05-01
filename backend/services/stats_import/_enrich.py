"""Post-processing for the import: UserName enrichment + library_name migration."""
import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

logger = logging.getLogger("mediakeeper.stats.import")


async def _enrich_usernames(db: AsyncSession, jf_users: list) -> None:
    """Update plugin PlaybackSession rows that lack UserName by looking up jf_users."""
    if not jf_users:
        return

    user_map = {u.get("Id", ""): u.get("Name", "") for u in jf_users if u.get("Id")}
    empty_name_rows = await db.execute(
        select(PlaybackSession).where(
            PlaybackSession.user_name == "",
            PlaybackSession.session_key.like("jsplugin_%"),
        )
    )
    updated_count = 0
    for row in empty_name_rows.scalars().all():
        name = user_map.get(row.user_id, "")
        if name:
            row.user_name = name
            updated_count += 1
    if updated_count:
        logger.info(f"Enriched {updated_count} plugin entries with UserName from jf_users")


async def _migrate_library_names(
    db: AsyncSession,
    item_to_library: dict,
    report: dict,
) -> None:
    """Fill library_name of existing PlaybackSession rows when it is NULL."""
    if not item_to_library:
        return

    null_lib_rows = await db.execute(
        select(PlaybackSession).where(
            PlaybackSession.library_name.is_(None),
            or_(
                PlaybackSession.session_key.like("js_%"),
                PlaybackSession.session_key.like("jsplugin_%"),
            )
        )
    )
    migrated = 0
    for row in null_lib_rows.scalars().all():
        lib = item_to_library.get(row.item_id)
        if not lib:
            if row.item_type == "Episode" or row.series_name:
                lib = "Séries"
            elif row.item_type == "Movie":
                lib = "Films"
        if lib:
            row.library_name = lib
            migrated += 1
    if migrated:
        logger.info(f"Migrated library_name on {migrated} existing entries")
        report["library_names_migrated"] = migrated
