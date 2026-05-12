"""Ranking + user title + rank tier + mini-leaderboard for the profile page.

Ranking is based on XP earned during the current calendar month. The
mini-leaderboard returns the top 5 users with their tier/title so the
frontend can render tier-colored avatars.
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal._display_name import resolve_display_name
from services.portal.profile_serializers import _resolve_avatar_url

logger = logging.getLogger("mediakeeper.portal.profile_stats")


def title_for_level(level: int) -> str:
    """Map user level → i18n title key."""
    if level >= 50: return "legend"
    if level >= 30: return "master"
    if level >= 20: return "expert"
    if level >= 12: return "passionate"
    if level >= 6:  return "regular"
    if level >= 3:  return "amateur"
    return "spectator"


def tier_for_title(title_key: str | None) -> int | None:
    """Resolve the rarity tier (1-6) of an unlocked-via-trophy title key."""
    if not title_key:
        return None
    try:
        from services.portal.achievement_defs import TITLE_REWARDS, ACHIEVEMENT_DEFS
        for ach_id, t_key in TITLE_REWARDS.items():
            if t_key == title_key:
                ach_def = next((d for d in ACHIEVEMENT_DEFS if d["id"] == ach_id), None)
                if ach_def:
                    return ach_def.get("tier", 1)
                break
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass
    return None


def tier_for_level(level: int) -> str:
    """Map current level → visual rank tier."""
    if level >= 50: return "legendary"
    if level >= 40: return "master"
    if level >= 30: return "diamond"
    if level >= 20: return "platinum"
    if level >= 11: return "gold"
    if level >= 6:  return "silver"
    return "bronze"


LEADERBOARD_VISIBLE = 15  # Top 15 always shown (B6).


async def _excluded_from_leaderboard(db: AsyncSession) -> list[int]:
    """Return user_ids of every profile that must NOT appear in the
    public ranking:

    - Non-Emby accounts (local-only profiles like the backoffice admin)
      — they don't represent a real streaming participant.
    - Deactivated MediaKeeper accounts (``account_active = False``) —
      a disabled user shouldn't keep climbing the leaderboard.
    - Soft-deleted accounts (``deleted_at`` set) — already invisible
      everywhere else, must stay invisible here too.

    Emby admins and moderators DO appear: the ranking is open to every
    Emby user regardless of their MediaKeeper role.
    """
    rows = (await db.execute(
        select(UserProfile.user_id).where(
            (UserProfile.source != "emby")
            | (UserProfile.emby_user_id.is_(None))
            | (UserProfile.account_active.is_(False))
            | (UserProfile.deleted_at.isnot(None))
        )
    )).scalars().all()
    return list(rows)


async def compute_leaderboard_only(
    db: AsyncSession, *, lang: str = "fr"
) -> list[dict]:
    """Return the top ``LEADERBOARD_VISIBLE`` users for the current month.

    Unlike :func:`compute_ranking`, this variant requires no viewer user
    — useful for surfaces where the caller is authenticated with the
    MediaKeeper admin cookie (``mk_token``) but doesn't necessarily have
    a Portal session. The backoffice dashboard widget uses it so it
    can render without forcing a Portal login first.
    """
    try:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = (month_start - timedelta(days=1)).replace(day=1)

        excluded_ids = await _excluded_from_leaderboard(db)

        current_stmt = (
            select(
                XpLedger.user_id,
                func.sum(XpLedger.xp).label("month_xp"),
            )
            .where(XpLedger.created_at >= month_start)
        )
        if excluded_ids:
            current_stmt = current_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        current_q = await db.execute(
            current_stmt
            .group_by(XpLedger.user_id)
            .order_by(desc("month_xp"))
            .limit(LEADERBOARD_VISIBLE)
        )
        leaders = current_q.all()
        if not leaders:
            return []

        # Previous-month ranks — only what we need to compute movement for
        # the current top N. Pulling the whole ledger would be wasteful.
        prev_stmt = (
            select(
                XpLedger.user_id,
                func.sum(XpLedger.xp).label("month_xp"),
            )
            .where(
                XpLedger.created_at >= prev_start,
                XpLedger.created_at < month_start,
            )
        )
        if excluded_ids:
            prev_stmt = prev_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        prev_q = await db.execute(
            prev_stmt
            .group_by(XpLedger.user_id)
            .order_by(desc("month_xp"))
        )
        prev_rank_by_user: dict[int, int] = {
            row.user_id: idx + 1 for idx, row in enumerate(prev_q.all())
        }

        leader_ids = [row.user_id for row in leaders]
        prof_rows = (await db.execute(
            select(UserProfile).where(UserProfile.user_id.in_(leader_ids))
        )).scalars().all() if leader_ids else []
        prof_by_id = {p.user_id: p for p in prof_rows}

        out: list[dict] = []
        for idx, row in enumerate(leaders):
            prof = prof_by_id.get(row.user_id)
            p_level = prof.level if prof else 1
            prev_r = prev_rank_by_user.get(row.user_id, 0)
            movement = (prev_r - (idx + 1)) if prev_r > 0 else 0
            effective = (
                None
                if prof is None or prof.display_name_must_set
                else prof.display_name
            )
            out.append({
                "rank": idx + 1,
                "user_id": row.user_id,
                "display_name": resolve_display_name(effective, row.user_id, lang),
                "avatar_url": _resolve_avatar_url(prof) if prof else None,
                "level": p_level,
                "tier": tier_for_level(p_level),
                "title_key": title_for_level(p_level),
                "month_xp": row.month_xp or 0,
                "selected_title": prof.selected_title if prof else None,
                "title_tier": tier_for_title(prof.selected_title if prof else None),
                "is_current_user": False,
                "movement": movement,
            })
        return out
    except Exception as e:
        logger.debug(f"[LEADERBOARD-ONLY] error: {e}")
        return []


async def compute_ranking(
    db: AsyncSession, user: User, *, lang: str = "fr"
) -> dict:
    """
    Compute the user's monthly XP ranking + percentile + movement vs
    last month + a mini-leaderboard of the top ``LEADERBOARD_VISIBLE``
    players with tier info.

    When the current user is ranked below the visible window they're
    appended as an extra "me" row so the UI can show them next to the
    leaders (with their real rank). Each entry carries its own
    ``movement`` field so the UI can draw a green/red arrow + delta.

    Returns ``{position, total, percentile, movement, leaderboard}``.
    """
    rank_position = 0
    rank_total = 0
    rank_percentile = 0
    rank_movement = 0
    leaderboard: list[dict] = []

    try:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        excluded_ids = await _excluded_from_leaderboard(db)

        all_stmt = (
            select(
                XpLedger.user_id,
                func.sum(XpLedger.xp).label("month_xp"),
            )
            .where(XpLedger.created_at >= month_start)
        )
        if excluded_ids:
            all_stmt = all_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        all_users_q = await db.execute(
            all_stmt
            .group_by(XpLedger.user_id)
            .order_by(desc("month_xp"))
        )
        all_users = all_users_q.all()
        rank_total = len(all_users)

        for idx, row in enumerate(all_users):
            if row.user_id == user.id:
                rank_position = idx + 1
                break

        if rank_position > 0 and rank_total > 0:
            rank_percentile = max(1, round(100 * rank_position / rank_total))

        prev_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_stmt = (
            select(
                XpLedger.user_id,
                func.sum(XpLedger.xp).label("month_xp"),
            )
            .where(
                XpLedger.created_at >= prev_start,
                XpLedger.created_at < month_start,
            )
        )
        if excluded_ids:
            prev_stmt = prev_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        prev_users_q = await db.execute(
            prev_stmt
            .group_by(XpLedger.user_id)
            .order_by(desc("month_xp"))
        )
        prev_users = prev_users_q.all()
        prev_rank_by_user: dict[int, int] = {
            row.user_id: idx + 1 for idx, row in enumerate(prev_users)
        }
        prev_position = prev_rank_by_user.get(user.id, 0)
        if prev_position > 0 and rank_position > 0:
            rank_movement = prev_position - rank_position  # positive = improved

        # Batch-fetch profiles for the leaders + optionally the current
        # user (added to the list below when out of the visible window).
        leader_ids = [row.user_id for row in all_users[:LEADERBOARD_VISIBLE]]
        needs_me = (
            rank_position > LEADERBOARD_VISIBLE
            and user.id not in leader_ids
        )
        lookup_ids = list(leader_ids)
        if needs_me:
            lookup_ids.append(user.id)
        prof_rows = (await db.execute(
            select(UserProfile).where(UserProfile.user_id.in_(lookup_ids))
        )).scalars().all() if lookup_ids else []
        prof_by_id = {p.user_id: p for p in prof_rows}

        def _entry_for(rank_idx: int, row) -> dict:
            prof = prof_by_id.get(row.user_id)
            p_level = prof.level if prof else 1
            prev_r = prev_rank_by_user.get(row.user_id, 0)
            movement = (prev_r - (rank_idx + 1)) if prev_r > 0 else 0
            effective = (
                None
                if prof is None or prof.display_name_must_set
                else prof.display_name
            )
            return {
                "rank": rank_idx + 1,
                "user_id": row.user_id,
                "display_name": resolve_display_name(effective, row.user_id, lang),
                "avatar_url": _resolve_avatar_url(prof) if prof else None,
                "level": p_level,
                "tier": tier_for_level(p_level),
                "title_key": title_for_level(p_level),
                "month_xp": row.month_xp or 0,
                "selected_title": prof.selected_title if prof else None,
                "title_tier": tier_for_title(prof.selected_title if prof else None),
                "is_current_user": row.user_id == user.id,
                "movement": movement,
            }

        for idx, row in enumerate(all_users[:LEADERBOARD_VISIBLE]):
            leaderboard.append(_entry_for(idx, row))

        if needs_me:
            # Find the actual row + rank index for the current user in
            # the full list, then append it so the UI can render them
            # right after the top N with a subtle separator.
            for idx, row in enumerate(all_users):
                if row.user_id == user.id:
                    leaderboard.append(_entry_for(idx, row))
                    break
    except Exception as e:
        logger.debug(f"[PROFILE] ranking error: {e}")

    return {
        "position": rank_position,
        "total": rank_total,
        "percentile": rank_percentile,
        "movement": rank_movement,
        "leaderboard": leaderboard,
    }
