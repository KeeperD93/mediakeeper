"""Release tags stripped from filenames before TMDB auto-search.

The frontend ``cleanName`` helper builds its strip regex from this list. The
defaults below cover the common release / encoding / source / language tags;
admins can override the list (add team-specific tags, remove a default that
clashes with a real title) via Media Manager → config → "Words to ignore".
"""
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting, set_setting

logger = logging.getLogger("mediakeeper.media_manager.release_tags")

SETTING_KEY = "media_manager.release_tags"
MAX_TAG_LENGTH = 64
MAX_TAGS = 500

# Built-in defaults. Each entry becomes a token in the strip regex, so a few
# entries (Customs?, AAC2, DDP5, DIRECTORS?\.?CUT, …) are written as small
# regex fragments rather than literal words.
DEFAULT_TAGS: list[str] = [
    # Resolutions
    "1080p", "720p", "480p", "576p", "2160p", "4K", "UHD", "HD", "SD",
    # Sources
    "BluRay", "BDRip", "BRRip", "WEBRip", "WEBDL", "WEB-DL", "WEB", "HDTV",
    "DVDRip", "DVD", "HDDVD", "HDLight", "HDRip",
    "CAM", "HDCAM", "TS", "PDVD", "PDTV", "WS",
    # Video codecs
    "x264", "x265", "H264", "H265", "HEVC", "AVC", "VP9", "AV1",
    # Audio codecs
    r"AAC\d?(?:\.\d)?", r"DTS(?:-HD|-MA|-X)?", "AC3", "MP3", "FLAC",
    r"DDP?\d?(?:\.\d)?", "EAC3", "TrueHD", "Atmos", "OPUS", "PCM",
    # Languages / dubs
    "MULTI", "FRENCH", "VOSTFR", "VOSTA", "VOST", "VFF", "VFI", "VF2?", "VO",
    # Streaming services
    "NF", "AMZN", "DSNP", "HMAX", "ATVP", "PCOK", "SHO",
    # HDR / bit depth
    "HDR", "SDR", r"HDR10\+?", "DV", "DOLBY", "10bit", "8bit", "10BITS?", "8BITS?",
    # Release groups / trackers
    "YGG", "YIFY", "RARBG",
    # Quality flags
    "PROPER", "REPACK", "INTERNAL", "HQ", "STF", "MiCaM", "READNFO", "NFO",
    "LIMITED", "EXTENDED", "REMASTERED", "THEATRICAL", "UNRATED",
    r"DIRECTORS?\.?CUT", "DC", "Customs?",
    # Pack / collection labels
    "Complete", "Completes?", "Integrales?", "Intégrales?", "Collection",
    "Coffret", "Pack", "Saisons?", "Seasons?", "Episodes?", "Épisodes?",
    "Serie", "Séries?", "Series", "Trilogy", "Trilogie", "Anthology", "Anthologie",
    # Doc tags
    "DOC", "DOCU", "Documentary", "Documentaire",
]


def _normalize(tag: str) -> str:
    return (tag or "").strip()


def _dedupe(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        if not isinstance(raw, str):
            continue
        tag = _normalize(raw)
        if not tag or len(tag) > MAX_TAG_LENGTH:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
        if len(out) >= MAX_TAGS:
            break
    return out


async def get_tags(db: AsyncSession) -> list[str]:
    raw = await get_setting(db, SETTING_KEY)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                cleaned = _dedupe([x for x in data if isinstance(x, str)])
                if cleaned:
                    return cleaned
        except json.JSONDecodeError:
            logger.warning("Corrupted release_tags setting — falling back to defaults")
    return list(DEFAULT_TAGS)


async def set_tags(db: AsyncSession, tags: list[str]) -> list[str]:
    cleaned = _dedupe(tags)
    await set_setting(db, SETTING_KEY, json.dumps(cleaned, ensure_ascii=False))
    return cleaned


async def reset_tags(db: AsyncSession) -> list[str]:
    await set_setting(db, SETTING_KEY, "")
    return list(DEFAULT_TAGS)
