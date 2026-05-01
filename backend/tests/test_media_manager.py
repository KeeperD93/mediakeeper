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
