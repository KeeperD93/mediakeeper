"""Global request status per TMDB id, for the portal "already requested" marks."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.requests import (
    REQUEST_APPROVED,
    REQUEST_AVAILABLE,
    REQUEST_PENDING,
    REQUEST_REJECTED,
)
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from services.portal._display_name import resolve_display_name
from services.portal.admin_users_constants import ROLE_ADMIN


async def get_batch_status(
    db: AsyncSession,
    tmdb_ids: list[int],
    *,
    anonymize: bool = False,
    lang: str = "fr",
) -> dict:
    """
    Return the most relevant request status per tmdb_id.

    Priority order (highest first):
        approved > pending > available > rejected

    ``rejected`` IS returned so MediaCard can surface the "Rejected"
    sash and swap the CTA to "Re-request" — but any fresher active
    status for the same item wins via the priority table.

    ``requested_by`` is the requester's public name, as the chat shows it:
    their pseudo, the generated one while they never picked theirs, the
    admin label for an admin. The sign-in name never leaves the server
    here, admins included: the admin request queue keeps it to moderate.
    The generated pseudo and the admin label follow ``lang``.

    When ``anonymize`` is True, ``requested_by``, ``requested_by_deleted``
    and ``reject_reason`` are stripped so the caller can't tell who filed
    or moderated each request — only status and date stay visible. Used
    for non-admins when the Portal-wide ``anonymize_requests`` flag is
    on; admins always see the full payload to moderate.

    Archived requests are left out, like in the Requests lists.
    """
    if not tmdb_ids:
        return {}

    # Pick the "best" (highest priority) status per tmdb_id.
    PRIO = {REQUEST_APPROVED: 3, REQUEST_PENDING: 2, REQUEST_AVAILABLE: 1, REQUEST_REJECTED: 0}
    rows = await db.execute(
        select(
            MediaRequest,
            UserProfile.display_name,
            UserProfile.display_name_must_set,
            UserProfile.role,
        )
        .join(UserProfile, UserProfile.user_id == MediaRequest.user_id, isouter=True)
        .where(
            MediaRequest.tmdb_id.in_(tmdb_ids),
            MediaRequest.status.in_(list(PRIO)),
            MediaRequest.archived_at.is_(None),
        )
        .order_by(MediaRequest.created_at.desc())
    )

    out: dict[str, dict] = {}
    for req, display, must_set, role in rows.all():
        key = str(req.tmdb_id)
        existing = out.get(key)
        new_prio = PRIO.get(req.status, 0)
        if existing and PRIO.get(existing["status"], 0) >= new_prio:
            continue
        entry: dict = {
            "status": req.status,
            "requested_at": req.created_at.isoformat() if req.created_at else None,
            "request_id": req.id,
            "retry_count": req.retry_count or 0,
        }
        if not anonymize:
            entry["reject_reason"] = (
                req.reject_reason if req.status == REQUEST_REJECTED else None
            )
            # ``user_id IS NULL`` after GDPR-purge (FK ``SET NULL`` since
            # migration 041). Flag it so the frontend renders an i18n
            # placeholder instead of ``user#None``.
            if req.user_id is None:
                entry["requested_by"] = None
                entry["requested_by_deleted"] = True
            else:
                entry["requested_by"] = resolve_display_name(
                    None if (must_set or display is None) else display,
                    req.user_id,
                    lang,
                    is_admin=role == ROLE_ADMIN,
                )
                entry["requested_by_deleted"] = False
        out[key] = entry
    return out
