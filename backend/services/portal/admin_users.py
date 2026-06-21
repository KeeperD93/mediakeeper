"""Premium admin user management — list, detail and identity updates.

Companion modules (see ``admin_users_*``):

- ``admin_users_serialize.py`` — row + detail serialisers, shared
- ``admin_users_actions.py``    — role / permissions / access / Emby toggle
- ``admin_users_lifecycle.py``  — notes / tags / soft-delete / restore / RGPD / bulk
- ``admin_users_emby.py``       — selective import + listing of unimported Emby users
- ``admin_users_audit.py``      — audit log read + helper

Every mutating endpoint must call ``record_audit`` so the trail on the
drawer "Audit" tab is complete.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile

from services.portal.requests_quota import get_user_quota
from .admin_users_audit import record_audit
from .admin_users_constants import (
    ACCESS_EXPIRY_WARNING_DAYS,
    ACTION_USER_UPDATED_IDENTITY,
)
from .admin_users_serialize import (
    now_utc,
    serialize_admin_user_detail,
    serialize_admin_user_row,
)


def _apply_filters(
    base_query,
    *,
    search: str | None,
    source: str | None,
    role: str | None,
    status: str | None,
    expires_within: int | None,
    include_deleted: bool,
    tag: str | None,
    pending_deletion: bool | None,
    ref,
):
    """Mutate ``base_query`` in-place to match the front-end filters."""
    if not include_deleted:
        base_query = base_query.where(UserProfile.deleted_at.is_(None))
    if pending_deletion:
        base_query = base_query.where(User.pending_deletion_at.isnot(None))

    if search:
        # ``#tag`` shorthand: treat the rest of the search as a tag
        # filter so admins can power-search from a single input.
        if search.startswith("#") and len(search) > 1:
            tag = (tag or search[1:]).strip()
        else:
            # autoescape: %/_ in the search are matched literally (ESCAPE
            # clause emitted so SQLite honours it, not only Postgres).
            base_query = base_query.where(
                or_(
                    UserProfile.display_name.icontains(search, autoescape=True),
                    User.username.icontains(search, autoescape=True),
                    UserProfile.email.icontains(search, autoescape=True),
                    UserProfile.first_name.icontains(search, autoescape=True),
                    UserProfile.last_name.icontains(search, autoescape=True),
                )
            )
    if source:
        base_query = base_query.where(UserProfile.source == source)
    if role:
        base_query = base_query.where(UserProfile.role == role)
    if tag:
        # JSON arrays: cast both sides to text and look for the exact
        # token. Quoted because the JSON serialiser wraps strings.
        from sqlalchemy import cast, String
        base_query = base_query.where(
            cast(UserProfile.tags, String).icontains(f'"{tag}"', autoescape=True)
        )

    if status == "active":
        base_query = base_query.where(
            and_(UserProfile.account_active.is_(True), User.is_active.is_(True))
        )
    elif status == "inactive":
        base_query = base_query.where(
            or_(UserProfile.account_active.is_(False), User.is_active.is_(False))
        )
    elif status == "expired":
        base_query = base_query.where(
            and_(
                UserProfile.access_end_date.isnot(None),
                UserProfile.access_end_date <= ref,
            )
        )
    elif status == "never_logged_in":
        base_query = base_query.where(UserProfile.last_login_at.is_(None))

    if expires_within is not None and expires_within > 0:
        deadline = ref + timedelta(days=expires_within)
        base_query = base_query.where(
            and_(
                UserProfile.access_end_date.isnot(None),
                UserProfile.access_end_date > ref,
                UserProfile.access_end_date <= deadline,
            )
        )
    return base_query


async def list_admin_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    source: str | None = None,
    role: str | None = None,
    status: str | None = None,
    expires_within: int | None = None,
    include_deleted: bool = False,
    tag: str | None = None,
    pending_deletion: bool | None = None,
    sort: str = "display_name",
    order: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Paginated list with filters used by the admin "Users" page.

    ``status`` can be: ``active``, ``inactive``, ``expired``,
    ``never_logged_in``. ``expires_within`` is a day count.
    ``pending_deletion=true`` restricts to users whose
    ``pending_deletion_at`` is set — used by the admin GDPR section.
    """
    ref = now_utc()
    base = (
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
    )
    base = _apply_filters(
        base,
        search=search,
        source=source,
        role=role,
        status=status,
        expires_within=expires_within,
        include_deleted=include_deleted,
        tag=tag,
        pending_deletion=pending_deletion,
        ref=ref,
    )

    sort_col = {
        "display_name": UserProfile.display_name,
        "username": User.username,
        "level": UserProfile.level,
        "xp": UserProfile.xp,
        "last_seen_at": UserProfile.last_seen_at,
        "access_end_date": UserProfile.access_end_date,
        "created_at": UserProfile.created_at,
    }.get(sort, UserProfile.display_name)
    base = base.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    total_q = (
        select(func.count(UserProfile.id))
        .select_from(UserProfile)
        .join(User, User.id == UserProfile.user_id)
    )
    total_q = _apply_filters(
        total_q,
        search=search,
        source=source,
        role=role,
        status=status,
        expires_within=expires_within,
        include_deleted=include_deleted,
        tag=tag,
        pending_deletion=pending_deletion,
        ref=ref,
    )
    total = (await db.execute(total_q)).scalar() or 0

    rows = (await db.execute(base.offset(offset).limit(limit))).all()
    items = [serialize_admin_user_row(profile, user) for profile, user in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "expiry_warning_days": ACCESS_EXPIRY_WARNING_DAYS,
    }


async def get_admin_user(
    db: AsyncSession, profile_id: int
) -> tuple[UserProfile, User] | None:
    """Fetch ``(profile, user)`` for the drawer header. Honours soft-delete."""
    row = (await db.execute(
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
        .where(UserProfile.id == profile_id)
    )).first()
    if not row:
        return None
    return row[0], row[1]


async def get_admin_user_detail(
    db: AsyncSession, profile_id: int
) -> dict[str, Any] | None:
    pair = await get_admin_user(db, profile_id)
    if not pair:
        return None
    profile, user = pair
    detail = serialize_admin_user_detail(profile, user)
    detail["quota"] = await get_user_quota(db, profile.user_id)
    return detail


async def update_user_identity(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    display_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    admin_user_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Admin-only update of the editable identity fields.

    Display name skips the 6-month rename cooldown enforced on the
    user-facing endpoint — admins can rename anyone at any time.

    Returns the freshly persisted user detail so the caller can rehydrate
    its local state without waiting for a follow-up GET round-trip.
    """
    changed: dict[str, str | None] = {}
    if display_name is not None:
        new_name = display_name.strip()[:50]
        if not new_name:
            return {"error": "display_name_empty"}
        if new_name != (profile.display_name or ''):
            changed["display_name"] = new_name
            profile.display_name = new_name
            profile.display_name_must_set = False
            profile.display_name_changed_at = now_utc()
    if first_name is not None:
        new_value = (first_name.strip() or None) if first_name else None
        if new_value != profile.first_name:
            profile.first_name = new_value
            changed["first_name"] = new_value
    if last_name is not None:
        new_value = (last_name.strip() or None) if last_name else None
        if new_value != profile.last_name:
            profile.last_name = new_value
            changed["last_name"] = new_value
    if email is not None:
        new_value = (email.strip() or None) if email else None
        if new_value != profile.email:
            profile.email = new_value
            changed["email"] = new_value
    if changed:
        db.add(profile)
        await record_audit(
            db,
            admin_user_id=admin_user_id,
            target_user_id=profile.user_id,
            action=ACTION_USER_UPDATED_IDENTITY,
            payload={"changed": list(changed.keys())},
            ip=ip,
            user_agent=user_agent,
            commit=False,
        )
        await db.commit()
        await db.refresh(profile)
    return {
        "ok": True,
        "changed": changed,
        "user": serialize_admin_user_detail(profile, user),
    }


async def touch_last_seen(db: AsyncSession, user_id: int) -> None:
    """Bump ``last_seen_at`` for the online indicator. Best-effort,
    swallow exceptions so a write conflict never breaks an API call."""
    try:
        profile = (await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if profile:
            profile.last_seen_at = now_utc()
            db.add(profile)
            await db.commit()
    except Exception:
        await db.rollback()
