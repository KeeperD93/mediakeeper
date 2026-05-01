"""Shared helpers: library name normalization, languages, SQL filters."""
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import LibraryCache


async def _get_library_name_map(db: AsyncSession) -> dict[str, str]:
    """
    Build a mapping to normalize library names.
    Merge folder names (e.g. 'mangasetanimes') with
    the real Emby names (e.g. 'Mangas & Animes') via LibraryCache.
    """
    result = await db.execute(select(LibraryCache))
    libs = result.scalars().all()
    mapping = {}
    for lib in libs:
        canonical = lib.name
        if not canonical:
            continue
        mapping[canonical] = canonical
        norm = re.sub(r'[^a-z0-9]', '', canonical.lower()
                      .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                      .replace('à', 'a').replace('â', 'a')
                      .replace('ô', 'o').replace('ù', 'u').replace('û', 'u')
                      .replace('î', 'i').replace('ï', 'i')
                      .replace('ç', 'c').replace('&', 'et'))
        mapping[norm] = canonical
    return mapping


def _normalize_library_name(name: str, lib_map: dict[str, str]) -> str:
    """Normalize a library name via the LibraryCache mapping."""
    if not name:
        return name
    if name in lib_map:
        return lib_map[name]
    norm = re.sub(r'[^a-z0-9]', '', name.lower()
                  .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                  .replace('à', 'a').replace('â', 'a')
                  .replace('ô', 'o').replace('ù', 'u').replace('û', 'u')
                  .replace('î', 'i').replace('ï', 'i')
                  .replace('ç', 'c').replace('&', 'et'))
    if norm in lib_map:
        return lib_map[norm]
    return name


def _merge_by_name(items: list[dict], name_key: str = "name", val_key: str = "plays") -> list[dict]:
    """Merge entries that share the same normalized name."""
    merged = {}
    for item in items:
        key = item[name_key]
        if key in merged:
            merged[key][val_key] += item[val_key]
        else:
            merged[key] = dict(item)
    return sorted(merged.values(), key=lambda x: x[val_key], reverse=True)


def _apply_filters(query, filters: list):
    """Apply a list of SQLAlchemy filters to a query."""
    for filter_ in filters:
        query = query.where(filter_)
    return query


_LANG_MAP = {
    "fre": "French", "fra": "French", "fr": "French",
    "eng": "English", "en": "English",
    "jpn": "Japanese", "ja": "Japanese",
    "ger": "German", "deu": "German", "de": "German",
    "spa": "Spanish", "es": "Spanish",
    "ita": "Italian", "it": "Italian",
    "por": "Portuguese", "pt": "Portuguese",
    "rus": "Russian", "ru": "Russian",
    "kor": "Korean", "ko": "Korean",
    "chi": "Chinese", "zho": "Chinese", "zh": "Chinese",
    "ara": "Arabic", "ar": "Arabic",
    "hin": "Hindi", "hi": "Hindi",
    "tha": "Thai", "th": "Thai",
    "pol": "Polish", "pl": "Polish",
    "dut": "Dutch", "nld": "Dutch", "nl": "Dutch",
    "swe": "Swedish", "sv": "Swedish",
    "nor": "Norwegian", "no": "Norwegian",
    "dan": "Danish", "da": "Danish",
    "fin": "Finnish", "fi": "Finnish",
    "tur": "Turkish", "tr": "Turkish",
    "ces": "Czech", "cze": "Czech", "cs": "Czech",
    "ron": "Romanian", "rum": "Romanian", "ro": "Romanian",
    "hun": "Hungarian", "hu": "Hungarian",
    "ell": "Greek", "gre": "Greek", "el": "Greek",
    "heb": "Hebrew", "he": "Hebrew",
    "vie": "Vietnamese", "vi": "Vietnamese",
    "ind": "Indonesian", "id": "Indonesian",
    "ukr": "Ukrainian", "uk": "Ukrainian",
    "und": "Undetermined",
}


def _lang_display(code: str) -> str:
    """Convert an ISO 639 language code to a readable name."""
    if not code:
        return "Unknown"
    return _LANG_MAP.get(code.lower(), code.upper())
