"""Plan, apply by hand and read back a watch XP recalculation, for its tests (fictitious data)."""
from datetime import datetime

from sqlalchemy import delete, select

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.watch_xp_recalc import Plan, PlayerPlan, build_context, plan_all
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def sign_in_as(client, db, name: str, role: str) -> None:
    user, _ = await make_portal_user(db, username=name, role=role)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


async def plan(db, as_of: datetime | None = None) -> Plan:
    return await plan_all(db, await build_context(db, as_of))


def player(found: Plan, user_id: int) -> PlayerPlan:
    return next(p for p in found.players if p.user_id == user_id)


def references(rows) -> list[str]:
    return [row.reference for row in rows]


async def apply(db, found: Plan) -> None:
    """What an application writes: the rows that go, the rows that come, XP and level."""
    for p in found.players:
        if not p.changed:
            continue
        if p.deleted:
            await db.execute(delete(XpLedger).where(XpLedger.id.in_([row.id for row in p.deleted])))
        db.add_all(
            XpLedger(user_id=p.user_id, action=t.action, reference=t.reference, xp=t.xp, created_at=t.at)
            for t in p.inserted
        )
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == p.user_id))).scalar_one()
        profile.xp, profile.level = p.xp_after, p.level_after
    await db.commit()


async def give(db, user_id: int, action: str, reference: str, xp: int, at: datetime) -> None:
    """A ledger row and its XP on the profile."""
    db.add(XpLedger(user_id=user_id, action=action, reference=reference, xp=xp, created_at=at))
    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one()
    profile.xp = (profile.xp or 0) + xp
    await db.commit()


async def sitting(db, name: str, item: str, at: datetime) -> None:
    """A playback never watched to its end."""
    db.add(PlaybackSession(
        session_key=f"emby-{name}_{item}_{at.timestamp()}", user_id=f"emby-{name}", user_name=name,
        item_id=item, item_name="Test Movie", item_type="Movie", started_at=at, is_active=False,
        watched_seconds=600, exclusive_seconds=600,
    ))
    await db.commit()
