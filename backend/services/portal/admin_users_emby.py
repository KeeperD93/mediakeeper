"""Selective Emby import + manual local user creation.

The legacy ``user_import.import_emby_users`` does a bulk pull, which
the refactored UI replaces with a two-step flow:

1. ``list_unimported_emby_users`` powers the import overlay (admin
   ticks the users they want).
2. ``import_selected_emby_users`` materialises only the selection.

Manual creation lands here too because both flows ultimately produce a
``User`` + ``UserProfile`` pair with the right ``source`` flag.
"""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.user import User
from models.user_preferences import UserPreference
from models.portal.profile import UserProfile
from services.emby.users import list_emby_users
from services.portal.profiles import resolve_unique_display_name

from .admin_users_audit import record_audit
from .admin_users_constants import (
    ACTION_USER_CREATED,
    ACTION_USER_IMPORTED,
    ROLES,
    ROLE_PRESETS,
    ROLE_VIEWER,
    SOURCE_EMBY,
    SOURCE_LOCAL,
)


async def backfill_emby_user_ids(db: AsyncSession) -> dict[str, Any]:
    """Reconcile every MK profile with its Emby counterpart in one pass:
    stamp ``emby_user_id`` (was empty pre-035), force ``source="emby"``
    on matches (some legacy profiles inherited ``local``), and mirror
    ``Policy.IsDisabled`` into ``emby_is_disabled`` so the list can flag
    upstream-blocked accounts without a per-row Emby round-trip."""
    emby_users = await list_emby_users(db)
    if not emby_users:
        return {"error": "no_source"}

    rows = (await db.execute(
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
    )).all()

    # Build a lookup that carries the Emby id + the disabled flag.
    by_username: dict[str, dict[str, Any]] = {}
    for eu in emby_users:
        name = (eu.get("Name") or "").lower()
        eid = eu.get("Id") or ""
        if not name or not eid:
            continue
        by_username[name] = {
            "id": eid,
            "is_disabled": bool((eu.get("Policy") or {}).get("IsDisabled")),
        }

    updated = 0
    already = 0
    unmatched = 0
    disabled_synced = 0
    for profile, user in rows:
        match = by_username.get((user.username or "").lower())
        if not match:
            unmatched += 1
            continue
        dirty = False
        if profile.emby_user_id != match["id"]:
            profile.emby_user_id = match["id"]
            dirty = True
        if profile.source != SOURCE_EMBY:
            profile.source = SOURCE_EMBY
            dirty = True
        if profile.emby_is_disabled != match["is_disabled"]:
            profile.emby_is_disabled = match["is_disabled"]
            dirty = True
            disabled_synced += 1
        if dirty:
            db.add(profile)
            updated += 1
        else:
            already += 1
    if updated:
        await db.commit()
    return {
        "ok": True,
        "updated": updated,
        "already_linked": already,
        "unmatched": unmatched,
        "disabled_synced": disabled_synced,
        "total_emby": len(emby_users),
    }


async def list_unimported_emby_users(db: AsyncSession) -> dict[str, Any]:
    """Return the Emby users that have no MediaKeeper account yet.

    Match is by lowercase ``Name`` against ``User.username`` and by Emby
    GUID against ``UserProfile.emby_user_id`` so a user that lost their
    account name doesn't get duplicated.
    """
    emby_users = await list_emby_users(db)
    if not emby_users:
        return {"items": [], "total_emby": 0}

    existing_usernames = {
        row.lower() for row in (await db.execute(select(User.username))).scalars().all()
    }
    existing_emby_ids = {
        row for row in (
            await db.execute(
                select(UserProfile.emby_user_id).where(UserProfile.emby_user_id.isnot(None))
            )
        ).scalars().all()
    }

    items = []
    for eu in emby_users:
        name = (eu.get("Name") or "").strip()
        emby_id = eu.get("Id") or ""
        if not name:
            continue
        if name.lower() in existing_usernames:
            continue
        if emby_id and emby_id in existing_emby_ids:
            continue
        items.append({
            "emby_user_id": emby_id,
            "username": name,
            "is_administrator": bool((eu.get("Policy") or {}).get("IsAdministrator")),
            "is_disabled": bool((eu.get("Policy") or {}).get("IsDisabled")),
            "last_login_date": eu.get("LastLoginDate"),
            "last_activity_date": eu.get("LastActivityDate"),
            "avatar_url": f"/api/emby/user-image/{emby_id}" if emby_id else None,
        })
    items.sort(key=lambda u: u["username"].lower())
    return {"items": items, "total_emby": len(emby_users)}


async def import_selected_emby_users(
    db: AsyncSession,
    *,
    emby_user_ids: Iterable[str],
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Create MK accounts for the requested subset of Emby users."""
    wanted = {eid for eid in emby_user_ids if eid}
    if not wanted:
        return {"error": "no_target"}

    emby_users = await list_emby_users(db)
    selected = [eu for eu in emby_users if (eu.get("Id") or "") in wanted]
    if not selected:
        return {"error": "not_found"}

    created = 0
    skipped = 0
    for eu in selected:
        emby_id = eu.get("Id") or ""
        emby_name = (eu.get("Name") or "").strip()
        if not emby_id or not emby_name:
            skipped += 1
            continue

        existing_user = (await db.execute(
            select(User).where(User.username == emby_name)
        )).scalar_one_or_none()
        if existing_user:
            skipped += 1
            continue

        user = User(
            username=emby_name,
            hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        await db.flush()

        unique_name = await resolve_unique_display_name(
            db, emby_name, exclude_user_id=user.id,
        )
        profile = UserProfile(
            user_id=user.id,
            display_name=unique_name,
            avatar_url=f"/api/emby/user-image/{emby_id}",
            role="viewer",
            source=SOURCE_EMBY,
            emby_user_id=emby_id,
            account_active=False,
            display_name_must_set=True,
        )
        db.add(profile)
        db.add(UserPreference(user_id=user.id))
        await record_audit(
            db,
            admin_user_id=admin_user_id,
            target_user_id=user.id,
            action=ACTION_USER_IMPORTED,
            payload={"emby_user_id": emby_id, "username": emby_name},
            ip=ip,
            user_agent=user_agent,
            commit=False,
        )
        created += 1

    await db.commit()
    return {"ok": True, "created": created, "skipped": skipped}


async def create_local_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    role: str = "viewer",
    account_active: bool = True,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Provision a brand-new MediaKeeper-only account.

    Used when the admin wants to grant access to someone who has no
    Emby account at all — the partner of a streamer, a beta tester,
    etc. They authenticate via ``username`` + ``password`` like any
    other MK user; ``source=local`` distinguishes them from imported
    profiles in the list view.
    """
    cleaned_username = (username or "").strip()
    if not cleaned_username or len(cleaned_username) < 3:
        return {"error": "invalid_username"}
    if not password or len(password) < 8:
        return {"error": "invalid_password"}

    existing = (await db.execute(
        select(User).where(User.username == cleaned_username)
    )).scalar_one_or_none()
    if existing:
        return {"error": "username_taken"}

    user = User(
        username=cleaned_username,
        hashed_password=hash_password(password),
        is_active=account_active,
        must_change_password=False,
    )
    db.add(user)
    await db.flush()

    unique_name = await resolve_unique_display_name(
        db, (display_name or cleaned_username), exclude_user_id=user.id,
    )
    final_role = role if role in ROLES else ROLE_VIEWER
    preset = ROLE_PRESETS.get(final_role, {})
    profile = UserProfile(
        user_id=user.id,
        display_name=unique_name,
        role=final_role,
        source=SOURCE_LOCAL,
        account_active=account_active,
        display_name_must_set=False,
        first_name=(first_name or None) or None,
        last_name=(last_name or None) or None,
        email=(email or None) or None,
        **preset,
    )
    db.add(profile)
    db.add(UserPreference(user_id=user.id))
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_CREATED,
        payload={"username": cleaned_username, "source": SOURCE_LOCAL, "role": role},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    await db.refresh(profile)
    return {"ok": True, "profile_id": profile.id, "user_id": user.id}
