"""Outils SRT : comparateur, fix-encoding, shift."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User

from ._schemas import CompareRequest, FixEncodingRequest, ShiftSrtRequest

router = APIRouter()


@router.post("/compare")
async def compare(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from services.subtitle_tools import compare_subtitles
    return await compare_subtitles(db, req.file_id_a, req.file_id_b, req.media_duration_sec)


@router.post("/fix-encoding")
async def fix_enc(
    req: FixEncodingRequest,
    _: User = Depends(get_current_user),
):
    from services.subtitle_tools import fix_encoding
    return fix_encoding(req.path)


@router.post("/shift-srt")
async def shift_srt_route(
    req: ShiftSrtRequest,
    _: User = Depends(get_current_user),
):
    """Shift timestamps in an SRT file."""
    from services.subtitle_tools import shift_srt
    return shift_srt(req.path, req.offset_ms)
