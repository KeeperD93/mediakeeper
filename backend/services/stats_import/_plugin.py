"""Import of jf_playback_reporting_plugin_data entries (legacy Jellystats history)."""
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from ._activity import _parse_date

logger = logging.getLogger("mediakeeper.stats.import")


def _parse_plugin_name(item_name_raw: str, item_type: str):
    """Parse 'Series - S01E03 - Episode' or 'Movie' -> (series_name, season, episode, item_name)."""
    series_name: str | None = None
    season_number: int | None = None
    episode_number: int | None = None
    item_name = item_name_raw

    if item_type == "Episode" and item_name_raw:
        se_match = re.search(r'[Ss](\d+)[Ee](\d+)', item_name_raw)
        if se_match:
            season_number = int(se_match.group(1))
            episode_number = int(se_match.group(2))
        parts = item_name_raw.split(' - ')
        if len(parts) >= 3:
            series_name = parts[0].strip()
            item_name = parts[-1].strip()
        elif len(parts) == 2:
            series_name = parts[0].strip()
            item_name = parts[1].strip()

    return series_name, season_number, episode_number, item_name


async def _import_plugin_reporting(
    db: AsyncSession,
    jf_plugin: list,
    existing_keys: set[str],
    item_to_library: dict,
    report: dict,
    now: datetime,
) -> None:
    """Iterate over jf_playback_reporting_plugin_data and create the matching PlaybackSession rows."""
    report["plugin_imported"] = 0
    report["plugin_skipped"] = 0
    report["plugin_errors"] = 0

    if not jf_plugin:
        return

    logger.info("Jellystats import: %s plugin reporting entries to process", len(jf_plugin))
    batch: list[PlaybackSession] = []

    for entry in jf_plugin:
        try:
            rowid = entry.get("rowid", "")
            if not rowid:
                report["plugin_errors"] += 1
                continue

            session_key = f"jsplugin_{rowid}"
            if session_key in existing_keys:
                report["plugin_skipped"] += 1
                continue

            item_type = entry.get("ItemType", "")
            series_name, season_number, episode_number, item_name = _parse_plugin_name(
                entry.get("ItemName", ""), item_type,
            )

            duration_sec = int(entry.get("PlayDuration", 0) or 0)
            position_ticks = duration_sec * 10_000_000

            started_at = _parse_date(entry.get("DateCreated", ""), now)

            duration_sec = min(duration_sec, 86400)
            ended_at = started_at + timedelta(seconds=duration_sec) if duration_sec > 0 else started_at

            row = PlaybackSession(
                session_key=session_key,
                user_id=entry.get("UserId", ""),
                user_name="",  # Plugin does not store UserName; enriched later via jf_users
                item_id=entry.get("ItemId", ""),
                item_name=item_name,
                item_type=item_type or ("Episode" if series_name else "Movie"),
                series_name=series_name,
                season_number=season_number,
                episode_number=episode_number,
                library_name=item_to_library.get(entry.get("ItemId", "")) or (
                    "Séries" if series_name
                    else "Films" if item_type == "Movie"
                    else None
                ),
                client_name=entry.get("ClientName", ""),
                device_name=entry.get("DeviceName", ""),
                ip_address=None,
                play_method=entry.get("PlaybackMethod", "DirectPlay"),
                container=None,
                video_codec=None,
                audio_codec=None,
                resolution=None,
                bitrate=None,
                duration_ticks=0,
                position_ticks=position_ticks,
                started_at=started_at,
                last_seen_at=ended_at,
                ended_at=ended_at,
                is_active=False,
            )
            batch.append(row)
            existing_keys.add(session_key)
            report["plugin_imported"] += 1

            if len(batch) >= 500:
                db.add_all(batch)
                await db.flush()
                batch = []

        except Exception as e:
            logger.warning("Error import plugin reporting: %s", e)
            report["plugin_errors"] += 1

    if batch:
        db.add_all(batch)
