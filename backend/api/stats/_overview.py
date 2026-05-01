"""Aggregated views: totals, detailed sessions, libraries, playback, records, charts."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import (
    get_daily_chart_data,
    get_detailed_sessions,
    get_global_totals,
    get_libraries_stats,
    get_playback_stats,
    get_records,
    get_weekly_heatmap,
)

router = APIRouter()


@router.get("/totals")
async def totals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Totaux globaux without limite de time."""
    return await get_global_totals(db)


@router.get("/sessions/detailed")
async def detailed_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Active sessions with full transcoding details."""
    return await get_detailed_sessions(db)


@router.get("/libraries")
async def libraries(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Per-library statistics."""
    return await get_libraries_stats(db)


@router.get("/playback")
async def playback(
    days: int = Query(30, ge=0, le=99999),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Playback statistics (top movies, series, etc.)."""
    return await get_playback_stats(db, days=days)


@router.get("/chart/daily")
async def daily_chart(
    days: int = Query(30, ge=1, le=9999),
    group_by: str = Query("library"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daily chart data (per library or per user)."""
    return await get_daily_chart_data(db, days=days, group_by=group_by)


@router.get("/heatmap")
async def heatmap(
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Heatmap weekly des playbacks."""
    return await get_weekly_heatmap(db, days=days)


@router.get("/records")
async def records(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Records, streaks et faits marquants."""
    return await get_records(db)
