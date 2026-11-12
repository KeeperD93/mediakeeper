"""Simulate a watch XP recalculation: plan every player in a read-only transaction,
then roll it back, whatever happened."""
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile

from ._context import build_context
from ._months import month_changes
from ._plan import plan_all
from ._summary import summarize


async def simulate_watch_xp_recalc(db: AsyncSession) -> dict:
    await db.commit()  # what the request read so far; SET TRANSACTION must come first
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SET TRANSACTION READ ONLY"))
    try:
        ctx = await build_context(db)
        plan = await plan_all(db, ctx)
        months = await month_changes(db, ctx, plan)
        changed = [player.user_id for player in plan.players if player.changed]
        names = dict((await db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(UserProfile.user_id.in_(changed))
        )).all())
    finally:
        await db.rollback()
    return summarize(ctx, plan, months, names)
