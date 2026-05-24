"""
Service Media Manager — Management des files media via filesystem local.
Package split into modules (Rule 9, <= 300 lines).

Media folders are exposed to the container via Docker volumes.
Les paths sont configureds soit via les variables MEDIA_*, soit via les
categorys savedes en base.
"""
from ._paths import (  # noqa: F401 -- cross-module re-exports consumed by api/media/* and tests
    VIDEO_EXTENSIONS,
    _ensure_within_media_roots,
    _is_allowed_path,
    _sanitize_name,
    _validate_name,
    _validate_path,
)
from .categories import MEDIA_FOLDERS, get_categories, load_categories, save_categories
from .files import list_files
from .move import check_move_conflicts, create_folders_batch, delete_file, move_file, move_file_overwrite
from .naming import (
    build_episode_name,
    build_movie_name,
    build_season_folder_name,
    build_series_folder_name,
    format_size,
    sanitize_filename,
)
from .release_tags import DEFAULT_TAGS as DEFAULT_RELEASE_TAGS, get_tags as get_release_tags, reset_tags as reset_release_tags, set_tags as set_release_tags
from .rename import apply_rename, apply_rename_batch, preview_rename

__all__ = [
    "MEDIA_FOLDERS",
    "VIDEO_EXTENSIONS",
    "apply_rename",
    "apply_rename_batch",
    "build_episode_name",
    "build_movie_name",
    "build_season_folder_name",
    "build_series_folder_name",
    "check_move_conflicts",
    "create_folders_batch",
    "delete_file",
    "DEFAULT_RELEASE_TAGS",
    "format_size",
    "get_categories",
    "get_release_tags",
    "list_files",
    "load_categories",
    "move_file",
    "move_file_overwrite",
    "preview_rename",
    "reset_release_tags",
    "sanitize_filename",
    "save_categories",
    "set_release_tags",
]
