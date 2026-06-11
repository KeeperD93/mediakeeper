"""Batch download + library audit."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.async_utils import safe_create_task
from core.database import AsyncSessionLocal, get_db
from models.user import User

from ._schemas import AuditRequest, BatchDownloadRequest

router = APIRouter()

# Temporary storage of audit results (in-memory, reset on restart)
_audit_results: dict = {"data": None}


@router.post("/batch-download")
async def start_batch(
    req: BatchDownloadRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from services.subtitle_batch import batch_download, get_batch_progress
    from services.subtitle_profiles import get_default_profile, get_profile

    progress = get_batch_progress()
    if progress.get("running"):
        raise HTTPException(status_code=409, detail="batch_already_running")

    profile = None
    if req.profile_id:
        profile = await get_profile(db, req.profile_id)
    if not profile:
        profile = await get_default_profile(db)
    if not profile:
        raise HTTPException(status_code=400, detail="no_profile_available")

    items = [it.model_dump() for it in req.items]

    async def _run_batch():
        async with AsyncSessionLocal() as bg_db:
            await batch_download(bg_db, items, profile)

    safe_create_task(_run_batch(), name="subtitles.batch_download")
    return {"started": True, "total": len(items)}


@router.get("/batch-progress")
async def batch_progress(
    _: User = Depends(get_current_user),
):
    from services.subtitle_batch import get_batch_progress
    return get_batch_progress()


@router.post("/batch-cancel")
async def batch_cancel_route(
    _: User = Depends(get_current_user),
):
    from services.subtitle_batch import cancel_batch
    cancel_batch()
    return {"cancelled": True}


@router.post("/audit")
async def start_audit(
    req: AuditRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from services.subtitle_audit import get_audit_progress, run_audit

    progress = get_audit_progress()
    if progress.get("running"):
        raise HTTPException(status_code=409, detail="audit_already_running")

    async def _run():
        async with AsyncSessionLocal() as bg_db:
            result = await run_audit(bg_db, languages=req.languages, library=req.library, checks=req.checks)
        _audit_results["data"] = result

    safe_create_task(_run(), name="subtitles.audit")
    return {"started": True}


@router.get("/audit-progress")
async def audit_progress(
    _: User = Depends(get_current_user),
):
    from services.subtitle_audit import get_audit_progress
    return get_audit_progress()


@router.get("/audit-results")
async def audit_results(
    _: User = Depends(get_current_user),
):
    return _audit_results.get("data") or {"summary": {}, "items": []}
