"""Portal ticket endpoints."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import require_admin, require_permission
from services.portal import tickets as ticket_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.emby import search as emby_search

router = APIRouter(prefix="/tickets", tags=["portal-tickets"])

VALID_ISSUE_TYPES = {"audio", "subtitles", "video", "metadata", "playback", "file", "other"}


class CreateTicket(BaseModel):
    emby_item_id: Optional[str] = Field(None, max_length=64)
    series_emby_id: Optional[str] = Field(None, max_length=64)
    tmdb_id: Optional[int] = None
    media_title: str = Field(..., min_length=1, max_length=500)
    media_type: str = Field(..., pattern="^(movie|series|season|episode|other)$")
    selected_seasons: Optional[list[dict]] = None
    issue_type: str = Field(..., min_length=1, max_length=30)
    priority: str = Field("minor", pattern="^(minor|blocking)$")
    description: str = Field(..., min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _check_media_anchor(self):
        # "other" tickets are explicitly off-library: no Emby anchor allowed.
        if self.media_type == "other":
            if self.emby_item_id or self.series_emby_id or self.selected_seasons:
                raise ValueError("other_ticket_must_have_no_emby_anchor")
        # Library tickets must point to *something* on Emby. Movies anchor on
        # emby_item_id; series/season/episode anchor on series_emby_id.
        if self.media_type == "movie" and not self.emby_item_id:
            raise ValueError("movie_ticket_requires_emby_item_id")
        if self.media_type in ("series", "season", "episode") and not self.series_emby_id:
            raise ValueError("series_ticket_requires_series_emby_id")
        return self


class TicketReplyBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|resolved|closed)$")


@router.get("")
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    issue_type: Optional[str] = Query(
        None,
        description="Comma-separated subset of audio,subtitles,video,metadata,playback,file,other",
    ),
    sort: Literal["newest", "oldest"] = "newest",
    cursor: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    user_id = None if profile.role == "admin" else user.id
    issue_types = _split_csv(issue_type, VALID_ISSUE_TYPES)
    return await ticket_svc.list_tickets(
        db, user_id,
        status_filter=status_filter,
        issue_types=issue_types,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )


def _split_csv(value: Optional[str], allowed: set[str]) -> Optional[list[str]]:
    """Parse a comma-separated query param against an allowlist.

    Empty / whitespace-only values are treated as "no filter" (None) so the
    UI can omit the param without crafting a special case.
    """
    if not value or not value.strip():
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return [p for p in parts if p in allowed] or None


@router.post("")
async def create_ticket(
    data: CreateTicket,
    background_tasks: BackgroundTasks,
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    if data.issue_type not in VALID_ISSUE_TYPES:
        raise HTTPException(status_code=400, detail="invalid_issue_type")
    user, _ = up
    result = await ticket_svc.create_ticket(db, user.id, data.model_dump())
    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        user.id,
        user.username,
        "ticket_created",
    )
    return result


@router.get("/emby/search")
async def search_emby_for_ticket(
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(10, ge=1, le=20),
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    """Library autocomplete for ticket creation.

    Restricts results to items already present on Emby — by design: a ticket
    targets a piece of content the user can actually watch. The "other"
    fallback in the UI handles off-library issues without hitting this
    endpoint.
    """
    return {"items": await emby_search.search_movies_and_series(db, q, limit=limit)}


@router.get("/emby/series/{series_id}/seasons")
async def list_emby_series_seasons(
    series_id: str,
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    """Seasons + episodes of an Emby series for the ticket season picker."""
    return {"seasons": await emby_search.list_series_seasons(db, series_id)}


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    result = await ticket_svc.get_ticket(db, ticket_id)
    if not result:
        raise HTTPException(status_code=404, detail="ticket_not_found")
    user, profile = up
    if result["user_id"] != user.id and profile.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return result


@router.post("/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: int,
    data: TicketReplyBody,
    up: tuple[User, UserProfile] = Depends(require_permission("can_problems")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    result = await ticket_svc.add_reply(
        db,
        ticket_id,
        user.id,
        data.content,
        is_admin=profile.role == "admin",
    )
    if "error" in result:
        status_code = 403 if result["error"] == "forbidden" else 404
        raise HTTPException(status_code=status_code, detail=result["error"])
    return result


@router.put("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await ticket_svc.update_ticket_status(db, ticket_id, data.status)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
