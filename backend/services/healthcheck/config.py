"""Default HealthCheck configuration + lists of obsolete codecs/containers."""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting

DEFAULT_CONFIG = {
    "obsolete_codecs_enabled": True,
    "obsolete_containers_enabled": True,
    "low_resolution_enabled": True,
    "min_resolution_height": 720,
    "low_bitrate_enabled": True,
    "min_video_bitrate_kbps": 1000,
    "no_audio_enabled": True,
    "large_file_enabled": True,
    "max_file_size_gb": 50,
    "hdr_no_sdr_enabled": True,
}

OBSOLETE_VIDEO_CODECS = {
    "mpeg2video", "mpeg4", "msmpeg4v3", "msmpeg4v2",
    "wmv3", "wmv2", "wmv1", "vc1", "divx", "xvid", "rv40", "rv30",
}
OBSOLETE_CONTAINERS = {"avi", "wmv", "flv", "rmvb", "rm", "asf", "divx"}


async def _load_config(db: AsyncSession) -> dict:
    """Charge la config from la BDD, merge with les defaults."""
    raw = await get_setting(db, "healthcheck_config")
    if raw:
        try:
            return {**DEFAULT_CONFIG, **json.loads(raw)}
        except Exception:
            pass
    return {**DEFAULT_CONFIG}
