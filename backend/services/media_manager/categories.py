"""Media category management (cache + dynamic MEDIA_FOLDERS proxy)."""
import os
import re
import json
import logging

from services.path_config import get_backup_dir, get_existing_path_roots

logger = logging.getLogger("mediakeeper.media_manager")

# Media paths — default categories read only from environment variables.
# No root is hardcoded in the code.
_DEFAULT_CATEGORY_SPECS = [
    ("telechargement", "Téléchargement", "MEDIA_TELECHARGEMENT"),
    ("films", "Films", "MEDIA_FILMS"),
    ("series", "Séries", "MEDIA_SERIES"),
    ("documentaires", "Documentaires", "MEDIA_DOCUMENTAIRES"),
    ("filmsdanimation", "Animation", "MEDIA_FILMS_ANIMATION"),
    ("mangasetanimes", "Mangas", "MEDIA_MANGAS"),
    ("seriesdocu", "Séries Docu", "MEDIA_SERIES_DOCU"),
    ("spectacles", "Spectacles", "MEDIA_SPECTACLES"),
    ("halloween", "Halloween", "MEDIA_HALLOWEEN"),
    ("noel", "Noël", "MEDIA_NOEL"),
]


def _slugify_category_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", value.lower())
    return key or "media"


def _make_unique_category_key(base_key: str, seen: set[str]) -> str:
    if base_key not in seen:
        seen.add(base_key)
        return base_key

    index = 2
    while f"{base_key}{index}" in seen:
        index += 1
    key = f"{base_key}{index}"
    seen.add(key)
    return key


def _get_root_categories() -> list[dict]:
    categories = []
    seen_keys: set[str] = set()

    try:
        backup_dir = get_backup_dir().resolve(strict=False)
    except (OSError, RuntimeError):
        backup_dir = None

    for root in get_existing_path_roots():
        try:
            resolved = root.resolve(strict=False)
        except (OSError, RuntimeError):
            continue

        if backup_dir is not None and resolved == backup_dir:
            continue

        label = resolved.name or str(resolved)
        key = _make_unique_category_key(_slugify_category_key(label), seen_keys)
        categories.append({
            "key": key,
            "label": label,
            "path": str(resolved),
        })

    return categories


def _get_default_categories() -> list[dict]:
    categories = []
    for key, label, env_name in _DEFAULT_CATEGORY_SPECS:
        path = os.getenv(env_name, "").strip()
        if not path:
            continue
        categories.append({"key": key, "label": label, "path": path})
    if categories:
        return categories

    categories.extend(_get_root_categories())
    return categories


# Mutable cache — reloaded from the DB via load_categories()
_categories_cache: list[dict] = []


def _build_media_folders() -> dict[str, str]:
    """Build the key→path dict from the categories cache."""
    return {c["key"]: c["path"] for c in _categories_cache if c.get("key") and c.get("path")}


# MEDIA_FOLDERS is a dynamic proxy recomputed on every access
class _MediaFoldersProxy(dict):
    def __getitem__(self, key): return _build_media_folders()[key]
    def get(self, key, default=None): return _build_media_folders().get(key, default)
    def __contains__(self, key): return key in _build_media_folders()
    def values(self): return _build_media_folders().values()
    def items(self): return _build_media_folders().items()
    def keys(self): return _build_media_folders().keys()
    def __iter__(self): return iter(_build_media_folders())
    def __len__(self): return len(_build_media_folders())


MEDIA_FOLDERS = _MediaFoldersProxy()


async def load_categories(db) -> list[dict]:
    """Load categories from the DB, fallback to defaults."""
    from services.settings import get_setting
    raw = await get_setting(db, "media_categories")
    if raw:
        try:
            cats = json.loads(raw)
            if isinstance(cats, list) and len(cats) > 0:
                _categories_cache.clear()
                _categories_cache.extend(cats)
                return cats
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    defaults = _get_default_categories()
    _categories_cache.clear()
    _categories_cache.extend(defaults)
    return list(defaults)


async def get_categories(db) -> list[dict]:
    """Return categories (from cache or DB)."""
    if not _categories_cache:
        return await load_categories(db)
    return list(_categories_cache)


async def save_categories(db, categories: list[dict]):
    """Persist categories to DB and refresh the cache."""
    from services.settings import set_setting
    await set_setting(db, "media_categories", json.dumps(categories, ensure_ascii=False))
    _categories_cache.clear()
    _categories_cache.extend(categories)
