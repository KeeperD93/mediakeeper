"""Premium admin "Users" page — Emby selective import + manual creation.

Routes mounted at ``/api/portal/admin/users``:

- ``GET    /emby/unimported``         — list every Emby user without a MK account yet
- ``POST   /emby/import``             — import a selection of Emby user ids, then check their trophies
- ``POST   /local``                   — provision an administrator's local account
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api._portal_admin_users_helpers import client_ip, client_ua
from api.auth import get_current_user, require_csrf
from core.database import get_db
from core.security import MAX_BCRYPT_PASSWORD_BYTES, password_byte_length
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.portal.admin_users_emby import (
    backfill_emby_user_ids,
    create_local_user,
    import_selected_emby_users,
    list_unimported_emby_users,
)

router = APIRouter(prefix="/api/portal/admin/users", tags=["portal-admin-users"])
logger = logging.getLogger("mediakeeper.api.portal_admin_users_emby")


@router.get("/emby/unimported")
async def get_unimported(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_unimported_emby_users(db)


@router.post("/emby/sync-ids")
async def post_sync_emby_ids(
    _csrf: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backfill ``emby_user_id`` on every existing profile by matching
    on ``username``. Run this once after migration 035 to enable the
    admin "Disable Emby" toggle for accounts created before the fix."""
    return await backfill_emby_user_ids(db)


class EmbyImportSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    emby_user_ids: list[str] = Field(..., min_length=1, max_length=200)


@router.post("/emby/import")
async def post_emby_import(
    data: EmbyImportSelection,
    request: Request,
    background_tasks: BackgroundTasks,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await import_selected_emby_users(
        db,
        emby_user_ids=data.emby_user_ids,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    if result.get("created"):
        # An imported account earns at once: its trophies come from its whole Emby
        # history now, not at its next play. A deactivated account is left alone.
        user_ids = (await db.execute(
            select(User.id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(UserProfile.emby_user_id.in_(data.emby_user_ids), User.is_active.is_(True))
        )).scalars().all()
        for user_id in user_ids:
            background_tasks.add_task(
                safe_check_all_achievements_in_new_session, user_id, "emby_import",
            )
    return result


class LocalUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=MAX_BCRYPT_PASSWORD_BYTES)
    display_name: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    account_active: bool = True

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, v: str) -> str:
        if password_byte_length(v) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(
                f"password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes"
            )
        return v


@router.post("/local")
async def post_create_local(
    data: LocalUserCreate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_local_user(
        db,
        username=data.username,
        password=data.password,
        display_name=data.display_name,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        account_active=data.account_active,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
