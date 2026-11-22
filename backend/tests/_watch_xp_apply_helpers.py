"""Apply a watch XP recalculation through its endpoints and read back what it wrote, for
its tests (fictitious data)."""
from datetime import UTC, timedelta
from pathlib import Path

from sqlalchemy import select

from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal.watch_xp_recalc import _run
from tests._watch_xp_helpers import T, account, watched
from tests._watch_xp_recalc_helpers import give, sign_in_as, sitting

SIMULATE = "/api/portal/admin/debug/watch-xp/simulate"
APPLY = "/api/portal/admin/debug/watch-xp/apply"
ARCHIVE = "mediakeeper_backup_20260308_120000_watch_xp_recalc.zip"
HOUR = timedelta(hours=1)


def fake_backups(monkeypatch) -> tuple[list[str], list[str]]:
    """The labels of the backups made; a part named in the second list is missing from them."""
    made: list[str] = []
    failed: list[str] = []

    async def fake_backup(db, label=""):
        made.append(label)
        return BackupResult(Path(ARCHIVE), tuple(failed))

    monkeypatch.setattr(_run, "create_backup", fake_backup)
    return made, failed


async def two_players(client, db) -> dict[str, int]:
    """Alice: a film paid by the former rule and never finished, a sign-in, 270 XP from
    before the ledger and a film watched to its end. Bob: an episode watched to its end."""
    await sign_in_as(client, db, "admin", "admin")
    alice, bob = await account(db, "alice"), await account(db, "bob")
    await sitting(db, "alice", "MOVIE-9", T - 3 * HOUR)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)
    await give(db, alice, "daily_login", "2026-03-07", 2, T - 2 * HOUR)
    profile = await profile_of(db, alice)
    profile.xp += 270
    await db.commit()
    film = await watched(db, "alice", at=T - HOUR)  # 2 h: 40
    episode = await watched(db, "bob", item="EP-1", item_type="Episode", runtime=2700, at=T + HOUR)  # 15
    return {"alice": alice, "bob": bob, "film": film, "episode": episode}


async def profile_of(db, user_id: int) -> UserProfile:
    query = select(UserProfile).where(UserProfile.user_id == user_id).execution_options(populate_existing=True)
    return (await db.execute(query)).scalar_one()


async def confirmation(client) -> dict:
    """What the card sends back to apply: the moment and the print of the simulation."""
    simulated = (await client.get(SIMULATE)).json()
    return {"as_of": simulated["as_of"], "plan": simulated["plan"]}


async def ledger_rows(db) -> dict[int, list[tuple]]:
    rows = (await db.execute(
        select(XpLedger.user_id, XpLedger.action, XpLedger.reference, XpLedger.xp, XpLedger.created_at)
        .order_by(XpLedger.user_id, XpLedger.reference)
    )).all()
    found: dict[int, list[tuple]] = {}
    for user_id, action, reference, xp, at in rows:
        found.setdefault(user_id, []).append((action, reference, xp, at.replace(tzinfo=UTC) if at.tzinfo is None else at))
    return found


async def snapshot(db) -> tuple:
    """The ledger, every profile's XP and level, and the actions of the journal."""
    profiles = (await db.execute(select(UserProfile.user_id, UserProfile.xp, UserProfile.level))).all()
    actions = (await db.execute(select(AdminAuditLog.action))).scalars().all()
    return await ledger_rows(db), sorted(profiles), actions


async def audit_rows(db) -> dict[str, list[AdminAuditLog]]:
    found: dict[str, list[AdminAuditLog]] = {}
    for row in (await db.execute(select(AdminAuditLog).order_by(AdminAuditLog.id))).scalars():
        found.setdefault(row.action, []).append(row)
    return found
