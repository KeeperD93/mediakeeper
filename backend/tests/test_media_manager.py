import shutil
import uuid
from pathlib import Path

import pytest

from services import media_manager


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_media_manager" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.mark.asyncio
async def test_load_categories_falls_back_to_path_roots(monkeypatch, db_session):
    root = _make_workspace_tmp()
    try:
        media_root = root / "medias"
        media_root.mkdir()
        (media_root / "Films").mkdir()
        (media_root / "demo.mkv").write_bytes(b"video")

        backup_root = root / "backups"
        backup_root.mkdir()

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", f"{media_root};{backup_root}")
        monkeypatch.setenv("BACKUP_PATH", str(backup_root))
        monkeypatch.delenv("MEDIA_TELECHARGEMENT", raising=False)
        monkeypatch.delenv("MEDIA_FILMS", raising=False)
        monkeypatch.delenv("MEDIA_SERIES", raising=False)
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])

        categories = await media_manager.load_categories(db_session)

        assert len(categories) == 1
        assert categories[0]["label"] == "medias"
        assert Path(categories[0]["path"]) == media_root.resolve()

        files = await media_manager.list_files(categories[0]["key"])

        assert isinstance(files, list)
        names = {item["name"] for item in files}
        assert "Films" in names
        assert "demo.mkv" in names
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_load_categories_excludes_descendants_of_backup_dir(monkeypatch, db_session):
    """A configured root that lives *inside* the backup directory must never
    surface as a media category. This protects nested layouts where an
    operator added the backup hierarchy to ``MEDIAKEEPER_PATH_ROOTS`` for the
    backup flow but did not mean to expose its contents as browsable media.
    """
    root = _make_workspace_tmp()
    try:
        media_root = root / "medias"
        media_root.mkdir()
        (media_root / "demo.mkv").write_bytes(b"video")

        backup_root = root / "backups"
        backup_root.mkdir()
        nested_in_backup = backup_root / "shard-a"
        nested_in_backup.mkdir()
        (nested_in_backup / "should_not_show.zip").write_bytes(b"backup-zip")

        monkeypatch.setenv(
            "MEDIAKEEPER_PATH_ROOTS",
            f"{media_root};{backup_root};{nested_in_backup}",
        )
        monkeypatch.setenv("BACKUP_PATH", str(backup_root))
        monkeypatch.delenv("MEDIA_TELECHARGEMENT", raising=False)
        monkeypatch.delenv("MEDIA_FILMS", raising=False)
        monkeypatch.delenv("MEDIA_SERIES", raising=False)
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])

        categories = await media_manager.load_categories(db_session)

        # Only the genuine media root makes it into the category list.
        paths = {c["path"] for c in categories}
        assert paths == {str(media_root.resolve())}
        labels = {c["label"] for c in categories}
        assert "shard-a" not in labels
        assert "backups" not in labels
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_local_path_does_not_traverse_into_backup_zone(monkeypatch):
    """``_resolve_local_path`` must not return a candidate sitting inside the
    backup zone, even when an Emby path tail happens to match a structurally
    identical directory under both the media root and the backup root.
    """
    from services.opensubtitles.paths import _resolve_local_path

    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        backup_root = root / "backups"
        backup_root.mkdir()

        # Same relative tail under both roots; the media-side file is the
        # legitimate target, the backup-side file is a decoy.
        media_movie = media_root / "Films" / "movie.mkv"
        media_movie.parent.mkdir(parents=True)
        media_movie.write_bytes(b"media")
        decoy = backup_root / "Films" / "movie.mkv"
        decoy.parent.mkdir(parents=True)
        decoy.write_bytes(b"backup-decoy")

        # Backup root listed FIRST in the env: without the hardening, the
        # resolver would happily return the decoy path under backups because
        # it matches the suffix earliest. The new filter must skip it.
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", f"{backup_root};{media_root}")
        monkeypatch.setenv("BACKUP_PATH", str(backup_root))

        resolved = await _resolve_local_path(None, "/emby/Films/movie.mkv")

        assert resolved == str(media_movie.resolve())
        assert "backups" not in resolved
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_local_path_returns_existing_path_inside_roots(monkeypatch):
    """Positive case for the fast-path: when Emby reports a path that
    exists at the same location inside the container AND sits under a
    configured media root, the resolver must return it verbatim. This
    guards against an over-aggressive future tightening that would
    accidentally break legitimate same-mount-tree deployments.
    """
    from services.opensubtitles.paths import _resolve_local_path

    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        legit = media_root / "Films" / "movie.mkv"
        legit.parent.mkdir(parents=True)
        legit.write_bytes(b"video")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        # Emby reports the same absolute path that exists inside our
        # container (shared mount tree, the most common case).
        resolved = await _resolve_local_path(None, str(legit))

        assert resolved == str(legit.resolve())
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_local_path_refuses_existing_file_outside_roots(monkeypatch):
    """Defence in depth: when Emby reports a path that exists at the same
    absolute location inside the container but sits outside the configured
    media roots, the resolver must not return it verbatim. A compromised
    Emby (or a shared mount tree) could otherwise feed arbitrary readable
    host files (``/etc/passwd``, ``/proc/*``, secrets in ``/data``) to
    downstream consumers (ffprobe, unlink…).
    """
    from services.opensubtitles.paths import _resolve_local_path

    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        outside = root / "outside.txt"
        outside.write_text("not_a_media_file", encoding="utf-8")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        resolved = await _resolve_local_path(None, str(outside))

        # Refusal contract: empty string when no root matches. Callers
        # (search / existing / remove) must treat this as a rejection.
        assert resolved == ""
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _setup_nested_backup_layout(monkeypatch):
    """Build a media root containing a nested ``backups/`` zone.

    Returns ``(workspace_root, media_root, backup_dir, key)`` where ``key`` is
    the media-manager category key bound to ``media_root``. Caller is
    responsible for ``shutil.rmtree(workspace_root)``.
    """
    workspace = _make_workspace_tmp()
    media_root = workspace / "media"
    media_root.mkdir()
    backup_dir = media_root / "backups"
    backup_dir.mkdir()
    (backup_dir / "mediakeeper_backup_20260101_010101.zip").write_bytes(b"backup-zip")
    (backup_dir / "shard-a").mkdir()

    # Genuine media subfolder used as a regression anchor.
    real_subfolder = media_root / "Films"
    real_subfolder.mkdir()
    (real_subfolder / "movie.mkv").write_bytes(b"video")

    monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))
    monkeypatch.delenv("MEDIA_TELECHARGEMENT", raising=False)
    monkeypatch.delenv("MEDIA_FILMS", raising=False)
    monkeypatch.delenv("MEDIA_SERIES", raising=False)
    # Force a single category bound to the media root, regardless of any
    # cached state from previous tests in the session.
    key = "media"
    monkeypatch.setattr(
        media_manager.categories,
        "_categories_cache",
        [{"key": key, "label": "media", "path": str(media_root.resolve())}],
    )
    return workspace, media_root, backup_dir, key


@pytest.mark.asyncio
async def test_list_files_hides_backup_zone_when_nested_in_media_root(monkeypatch):
    """When ``BACKUP_PATH`` is a child of a configured media root, the backup
    folder must not appear in ``list_files`` of that media root."""
    workspace, media_root, backup_dir, key = _setup_nested_backup_layout(monkeypatch)
    try:
        items = await media_manager.list_files(key)

        assert isinstance(items, list)
        names = {it["name"] for it in items}
        # Genuine media subfolder is still listable (regression anchor).
        assert "Films" in names
        # Backup folder is filtered out, even though it sits inside media_root.
        assert "backups" not in names
        for item in items:
            assert "backups" not in Path(item["path"]).parts
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_list_files_into_backup_zone_returns_path_not_allowed(monkeypatch):
    """Drilling into the backup folder via ``subpath`` must be refused with
    the public ``path_not_allowed`` code, not silently return an empty list."""
    workspace, media_root, backup_dir, key = _setup_nested_backup_layout(monkeypatch)
    try:
        result = await media_manager.list_files(key, "backups")

        assert result == {"error": "path_not_allowed"}
        # Defence in depth: drilling deeper into the backup zone is also rejected.
        result_deep = await media_manager.list_files(key, "backups/shard-a")
        assert result_deep == {"error": "path_not_allowed"}
        # And the regression anchor (real media subfolder) still works.
        result_real = await media_manager.list_files(key, "Films")
        assert isinstance(result_real, list)
        assert {it["name"] for it in result_real} == {"movie.mkv"}
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_delete_file_refuses_backup_dir_and_descendants(monkeypatch):
    """``delete_file`` must refuse to delete the backup folder itself, any
    descendant file or folder, and never touch the bytes on disk."""
    workspace, media_root, backup_dir, _ = _setup_nested_backup_layout(monkeypatch)
    try:
        backup_zip = backup_dir / "mediakeeper_backup_20260101_010101.zip"
        nested = backup_dir / "shard-a"

        result_dir = await media_manager.delete_file(str(backup_dir))
        assert result_dir == {"error": "path_not_allowed"}
        result_zip = await media_manager.delete_file(str(backup_zip))
        assert result_zip == {"error": "path_not_allowed"}
        result_nested = await media_manager.delete_file(str(nested))
        assert result_nested == {"error": "path_not_allowed"}

        # On-disk state untouched.
        assert backup_dir.exists() and backup_dir.is_dir()
        assert backup_zip.exists() and backup_zip.read_bytes() == b"backup-zip"
        assert nested.exists() and nested.is_dir()

        # Regression: a real media file under the same media root deletes fine.
        movie = media_root / "Films" / "movie.mkv"
        ok = await media_manager.delete_file(str(movie))
        assert ok == {"success": True}
        assert not movie.exists()
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_move_file_refuses_when_source_or_destination_is_backup(monkeypatch):
    """``move_file`` must refuse if either side of the move is in the backup
    zone, with no mutation on disk."""
    workspace, media_root, backup_dir, _ = _setup_nested_backup_layout(monkeypatch)
    try:
        movie = media_root / "Films" / "movie.mkv"

        # Destination inside backup zone: refused.
        result_dest = await media_manager.move_file(str(movie), str(backup_dir))
        assert result_dest == {"error": "path_not_allowed"}
        assert movie.exists()
        assert not (backup_dir / "movie.mkv").exists()

        # Source inside backup zone: refused.
        backup_zip = backup_dir / "mediakeeper_backup_20260101_010101.zip"
        result_src = await media_manager.move_file(str(backup_zip), str(media_root / "Films"))
        assert result_src == {"error": "path_not_allowed"}
        assert backup_zip.exists() and backup_zip.read_bytes() == b"backup-zip"

        # Regression: legitimate move between media subfolders still works.
        new_home = media_root / "Spectacles"
        new_home.mkdir()
        ok = await media_manager.move_file(str(movie), str(new_home))
        assert ok.get("success") is True
        assert (new_home / "movie.mkv").exists()
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_apply_rename_refuses_backup_dir_and_descendants(monkeypatch):
    """``apply_rename`` must refuse to rename the backup folder, its children,
    and never touch the bytes on disk."""
    workspace, media_root, backup_dir, _ = _setup_nested_backup_layout(monkeypatch)
    try:
        backup_zip = backup_dir / "mediakeeper_backup_20260101_010101.zip"

        result_dir = await media_manager.apply_rename(str(backup_dir), "evil")
        assert result_dir == {"error": "path_not_allowed"}
        assert backup_dir.exists() and (backup_dir / "shard-a").is_dir()
        assert not (media_root / "evil").exists()

        result_zip = await media_manager.apply_rename(str(backup_zip), "stolen.zip")
        assert result_zip == {"error": "path_not_allowed"}
        assert backup_zip.exists() and backup_zip.read_bytes() == b"backup-zip"

        # Regression: renaming a real media subfolder still works.
        old_films = media_root / "Films"
        ok = await media_manager.apply_rename(str(old_films), "Films-2026")
        assert ok.get("success") is True
        assert (media_root / "Films-2026").is_dir()
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_create_folders_batch_refuses_under_backup(monkeypatch):
    """``create_folders_batch`` must refuse any creation under the backup
    zone (including the directory itself as parent) without leaving stray
    folders on disk."""
    workspace, media_root, backup_dir, _ = _setup_nested_backup_layout(monkeypatch)
    try:
        results = await media_manager.create_folders_batch([
            {"parent_path": str(backup_dir), "folder_name": "Trojan"},
            {"parent_path": str(backup_dir / "shard-a"), "folder_name": "Trojan"},
            # Regression: a legitimate media subfolder creation still succeeds.
            {"parent_path": str(media_root / "Films"), "folder_name": "Saison 1"},
        ])

        assert results[0]["error"] == "path_not_allowed"
        assert results[1]["error"] == "path_not_allowed"
        assert results[2].get("success") is True

        assert not (backup_dir / "Trojan").exists()
        assert not (backup_dir / "shard-a" / "Trojan").exists()
        assert (media_root / "Films" / "Saison 1").is_dir()
    finally:
        monkeypatch.setattr(media_manager.categories, "_categories_cache", [])
        shutil.rmtree(workspace, ignore_errors=True)
