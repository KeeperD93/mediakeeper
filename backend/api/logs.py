"""
Routes API for la management des journaux (logs).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from core.database import get_db
from api.auth import get_current_user
from models.user import User
from services.logs import get_log_files, read_log_file, get_log_filepath
from services.logs import MAX_LOG_LINES
from services.settings import get_setting, set_setting

logger = logging.getLogger("mediakeeper.api.logs")

router = APIRouter(prefix="/api/logs", tags=["logs"])


class DebugModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


@router.get("/files")
async def list_log_files(_: User = Depends(get_current_user)):
    """Return the list of log files with metadata."""
    files = get_log_files()
    return {"files": files}


@router.get("/read/{filename}")
async def read_log(
    filename: str,
    lines: int = Query(default=MAX_LOG_LINES, ge=1, le=MAX_LOG_LINES),
    _: User = Depends(get_current_user),
):
    """Read the last N lines of a log file (newest first)."""
    result = read_log_file(filename, lines=lines)
    if "error" in result and result["error"] == "file_not_found":
        raise HTTPException(status_code=404, detail="file_not_found")
    if "error" in result and result["error"] == "invalid_filename":
        raise HTTPException(status_code=400, detail="invalid_filename")
    return result


@router.get("/download/{filename}")
async def download_log(
    filename: str,
    _: User = Depends(get_current_user),
):
    """Download a log file."""
    filepath = get_log_filepath(filename)
    if not filepath:
        raise HTTPException(status_code=404, detail="file_not_found")
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="text/plain",
    )


@router.get("/debug")
async def get_debug_mode(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the debug-mode status."""
    value = await get_setting(db, "logs.debug_mode")
    enabled = value == "true"
    return {"enabled": enabled}


@router.post("/debug")
async def set_debug_mode(
    req: DebugModeRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Enable or disable debug mode."""
    await set_setting(db, "logs.debug_mode", "true" if req.enabled else "false")

    # Apply the level to the mediakeeper logger AND the file handler so DEBUG
    # lines actually reach the log file (not just the console). Shared with the
    # startup path so the two can never drift out of sync again.
    from core.app_startup import apply_debug_level
    apply_debug_level(req.enabled)
    logger.info("Debug mode %s", "ENABLED (DEBUG)" if req.enabled else "DISABLED (INFO)")

    return {"success": True, "enabled": req.enabled}
