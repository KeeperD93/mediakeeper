"""Endpoints : restore from file existant, upload-restore ZIP et JSON."""
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import (
    get_backup_path,
    get_current_backup_dir,
    restore_backup,
    restore_json_backup,
)
from services.backup.restore import BackupRestoreError, InvalidBackupArchiveError

from ._schemas import RestoreRequest
from ._shared import _parse_components_payload, _save_upload_to_path, logger

_RESTORE_WARNING = "This restore does NOT replay pg_dump.sql; restore PostgreSQL relational data manually first — see docs/operations/backup-restore.md."

router = APIRouter()


@router.post("/restore")
async def restore_backup_endpoint(
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    path = get_backup_path(req.filename)
    if not path:
        raise HTTPException(status_code=404, detail="backup_not_found")
    try:
        results = await restore_backup(db, path, components=req.components)
    except InvalidBackupArchiveError:
        raise HTTPException(status_code=400, detail="invalid_or_corrupted_zip")
    except BackupRestoreError:
        raise HTTPException(status_code=500, detail="backup_restore_failed")
    return {"success": True, "results": results, "warning": _RESTORE_WARNING}


@router.post("/upload-restore")
async def upload_and_restore(
    file: UploadFile = File(...),
    components: str = "{}",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Upload a backup ZIP file and restore it immediately."""
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="file_must_be_zip")

    backup_dir = get_current_backup_dir()
    tmp = backup_dir / f"__upload_{uuid4().hex}.zip"
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        await _save_upload_to_path(file, tmp)
        opts = _parse_components_payload(components)
        try:
            results = await restore_backup(db, tmp, components=opts)
        except InvalidBackupArchiveError:
            raise HTTPException(status_code=400, detail="invalid_or_corrupted_zip")
        except BackupRestoreError:
            raise HTTPException(status_code=500, detail="backup_restore_failed")
        return {"success": True, "results": results, "warning": _RESTORE_WARNING}
    finally:
        await file.close()
        if tmp.exists():
            tmp.unlink()


@router.post("/upload-restore-json")
async def upload_and_restore_json(
    file: UploadFile = File(...),
    components: str = "{}",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Upload un file JSON de backup et le restaure."""
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="file_must_be_json")

    backup_dir = get_current_backup_dir()
    tmp = backup_dir / f"__upload_{uuid4().hex}.json"
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        await _save_upload_to_path(file, tmp)
        data = json.loads(tmp.read_text(encoding="utf-8"))
        opts = _parse_components_payload(components)
        try:
            results = await restore_json_backup(db, data, components=opts)
        except BackupRestoreError:
            raise HTTPException(status_code=500, detail="backup_restore_failed")
        if any(str(status).startswith("error:") for status in results.values()):
            raise HTTPException(status_code=500, detail="backup_restore_failed")
        return {"success": True, "results": results, "warning": _RESTORE_WARNING}
    except HTTPException:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="json_file_invalid")
    except Exception as e:
        logger.error(f"[backup] Error restauration JSON: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="backup_restore_failed")
    finally:
        await file.close()
        if tmp.exists():
            tmp.unlink()
