"""Import of jf_playback_activity entries (Jellystats playbacks)."""
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

logger = logging.getLogger("mediakeeper.stats.import")


def _parse_se(item_name: str) -> tuple[int | None, int | None, str]:
    """Extract (season, episode, episode_title) from 'Series - S01E06 - Title'."""
    se_match = re.search(r'S(\d+)E(\d+)', item_name)
    season_number: int | None = None
    episode_number: int | None = None
    if se_match:
        season_number = int(se_match.group(1))
        episode_number = int(se_match.group(2))
        parts = item_name.split(' - ')
        if len(parts) >= 3:
            item_name = parts[-1].strip()
        elif len(parts) == 2:
            item_name = parts[-1].strip()
    return season_number, episode_number, item_name


def _parse_date(date_str: str, fallback: datetime) -> datetime:
    if not date_str:
        return fallback
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return fallback


async def _import_playback_activity(
    db: AsyncSession,
    jf_activity: list,
    existing_keys: set[str],
    item_to_library: dict,
    report: dict,
    now: datetime,
) -> None:
    """Iterate over jf_playback_activity and create the matching PlaybackSession rows."""
    logger.info(f"Jellystats import: {len(jf_activity)} playback entries to process")

    if jf_activity:
        sample = jf_activity[0]
        date_fields = [k for k in sample.keys() if any(d in k.lower() for d in ("date", "time", "created", "insert"))]
        logger.info(f"[import] Date fields detected in jf_playback_activity: {date_fields}")
        logger.info(f"[import] Example: { {k: sample.get(k) for k in date_fields} }")

    batch: list[PlaybackSession] = []

    for entry in jf_activity:
        try:
            js_id = entry.get("Id", "")
            if not js_id:
                report["playback_errors"] += 1
                continue

            session_key = f"js_{js_id}"
            if session_key in existing_keys:
                report["playback_skipped"] += 1
                continue

            series_name = entry.get("SeriesName")
            item_type = "Episode" if series_name else "Movie"

            season_number = None
            episode_number = None
            item_name = entry.get("NowPlayingItemName", "")
            if series_name and item_name:
                season_number, episode_number, item_name = _parse_se(item_name)

            streams = entry.get("MediaStreams", [])
            video_stream = next((s for s in streams if s.get("Type") == "Video"), {})
            audio_stream = next((s for s in streams if s.get("Type") == "Audio" and s.get("IsDefault")), None)
            if not audio_stream:
                audio_stream = next((s for s in streams if s.get("Type") == "Audio"), {})
            else:
                audio_stream = audio_stream or {}

            height = video_stream.get("Height", 0)
            resolution = (
                "4K" if height >= 2100 else
                "1080p" if height >= 1000 else
                "720p" if height >= 700 else
                "SD" if height > 0 else None
            )

            play_method = entry.get("PlayMethod", "DirectPlay")
            if entry.get("TranscodingInfo"):
                play_method = "Transcode"

            duration_sec = int(entry.get("PlaybackDuration", 0) or 0)
            position_ticks = duration_sec * 10_000_000

            date_str = (entry.get("ActivityDateInserted")
                        or entry.get("DateCreated")
                        or entry.get("Date")
                        or entry.get("date")
                        or "")
            started_at = _parse_date(date_str, now)

            duration_sec = min(duration_sec, 86400)  # Cap 24h
            ended_at = started_at + timedelta(seconds=duration_sec) if duration_sec > 0 else started_at

            item_id_str = entry.get("NowPlayingItemId", "")
            episode_id_str = entry.get("EpisodeId", "")
            library_name = item_to_library.get(episode_id_str) or item_to_library.get(item_id_str)
            if not library_name:
                if item_type == "Episode":
                    library_name = "Séries"
                elif item_type == "Movie":
                    library_name = "Films"

            row = PlaybackSession(
                session_key=session_key,
                user_id=entry.get("UserId", ""),
                user_name=entry.get("UserName", ""),
                item_id=entry.get("NowPlayingItemId", ""),
                item_name=item_name,
                item_type=item_type,
                series_name=series_name,
                season_number=season_number,
                episode_number=episode_number,
                library_name=library_name,
                client_name=entry.get("Client", ""),
                device_name=entry.get("DeviceName", ""),
                ip_address=entry.get("RemoteEndPoint", ""),
                play_method=play_method,
                container=entry.get("OriginalContainer", ""),
                video_codec=video_stream.get("Codec", "").upper() or None,
                audio_codec=audio_stream.get("Codec", "").upper() if audio_stream else None,
                resolution=resolution,
                bitrate=video_stream.get("BitRate"),
                duration_ticks=0,
                position_ticks=position_ticks,
                started_at=started_at,
                last_seen_at=ended_at,
                ended_at=ended_at,
                is_active=False,
            )
            batch.append(row)
            existing_keys.add(session_key)
            report["playback_imported"] += 1

            if len(batch) >= 500:
                db.add_all(batch)
                await db.flush()
                batch = []

        except Exception as e:
            logger.warning(f"Error importing Jellystats entry: {e}")
            report["playback_errors"] += 1

    if batch:
        db.add_all(batch)
