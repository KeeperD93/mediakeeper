"""Steps shared by the migration 073 tests: views through the real collector, then the backfill."""
import importlib.util
from datetime import datetime
from types import SimpleNamespace

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from api.stats._activity import delete_activity
from models.playback_stats import PlaybackCompletion, PlaybackSession
from tests._migration_helpers import BACKEND_ROOT
from tests._watch_measurement_helpers import STEP, emby_session, poll

REVISION = "073_completion_exclusive_seconds"
RUNTIME = 600
PAID = RUNTIME * 0.75  # watch XP: 75 % of the runtime watched alone
_ADMIN = SimpleNamespace(username="Alice")


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_073_under_test", BACKEND_ROOT / "alembic" / "versions" / f"{REVISION}.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def migrate(db, step) -> None:
    def run(sync_conn):
        with Operations.context(MigrationContext.configure(sync_conn)):
            step()

    await (await db.connection()).run_sync(run)
    await db.commit()


async def watch(db, start: datetime, first: int, last: int, *titles: tuple[str, str, int]) -> None:
    """Polls ``first`` to ``last``, 5 s apart; each ``(item, session, last poll)`` plays 5 s a poll."""
    at = start
    for i in range(first, last + 1):
        at = start + STEP * i
        await poll(db, at, *[
            emby_session(at=at, position_s=5 * i, item=item, session=session, runtime_s=RUNTIME)
            for item, session, until in titles if i <= until
        ])
    await poll(db, at + STEP)  # every player gone: the rows close


async def live_values(db) -> dict[int, int]:
    found = await db.execute(select(PlaybackCompletion.id, PlaybackCompletion.exclusive_seconds))
    return dict(found.all())


async def _sitting_of(db, session: str) -> PlaybackSession:
    return await db.scalar(select(PlaybackSession).where(PlaybackSession.emby_session_key.endswith(f"_{session}")))


async def done_of(db, session: str) -> int:
    row = await _sitting_of(db, session)
    return await db.scalar(select(PlaybackCompletion.id).where(PlaybackCompletion.session_id == row.id))


async def admin_deletes(db, session: str) -> None:
    """Statistics > Activity > delete: the sitting's watched title goes with it."""
    await delete_activity(activity_id=(await _sitting_of(db, session)).id, db=db, _=_ADMIN)


async def backfilled(db) -> dict[int, int]:
    await db.execute(sa.update(PlaybackCompletion).values(exclusive_seconds=0))  # as before 073
    await migrate(db, load_migration().upgrade)
    return await live_values(db)
