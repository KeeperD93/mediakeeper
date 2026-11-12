"""What every player of a watch XP recalculation shares, read once and free of ORM
objects so it outlives the read-only transaction it comes from."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.portal.xp_boost import XpBoostEvent
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.instance_time import get_instance_zone
from services.portal.achievements_utils import _coerce_utc
from services.portal.exclusions import load_exclusion_entries
from services.portal.gdpr_erased import load_erased_identities
from services.portal.xp import COMPLETION_MARK, LINKED_ACCOUNT, WATCH_XP_ACTIONS

# The former rule paid a title when its playback closed, after the title counted as watched.
LEDGER_START_MARGIN = timedelta(hours=1)
WATCH_ACTIONS = tuple(WATCH_XP_ACTIONS.values())


@dataclass(frozen=True)
class BonusEvent:
    """An XP event, with the fields ``multiplier_at`` reads."""

    id: int
    name: str
    multiplier: float
    starts_at: datetime
    ends_at: datetime
    action_filter: str | None
    enabled: bool


@dataclass(frozen=True)
class Context:
    as_of: datetime
    # Titles watched before it were paid before the ledger kept anything; None: empty ledger.
    ledger_start: datetime | None
    exclusions: tuple[dict, ...]
    events: tuple[BonusEvent, ...]
    erased: frozenset[str]
    zone: tzinfo
    # The accounts recalculated, deactivated or expired ones included: account id -> Emby id.
    scope: dict[int, str]


def this_rule_rows():
    """Watch rows of the current rule (``<item>:c<id>``): the rows a recalculation writes."""
    return and_(XpLedger.action.in_(WATCH_ACTIONS), XpLedger.reference.contains(COMPLETION_MARK, autoescape=True))


async def _ledger_start(db: AsyncSession) -> datetime | None:
    """The first instant the ledger kept. A row of the current rule counts as dated, without
    the margin: dated by its title, it never moves the start earlier, so a run after an
    applied one finds the same titles too old."""
    former = _coerce_utc(await db.scalar(select(func.min(XpLedger.created_at)).where(not_(this_rule_rows()))))
    current = _coerce_utc(await db.scalar(select(func.min(XpLedger.created_at)).where(this_rule_rows())))
    starts = [moment for moment in (former and former - LEDGER_START_MARGIN, current) if moment]
    return min(starts, default=None)


async def build_context(db: AsyncSession, as_of: datetime | None = None) -> Context:
    events = (await db.execute(
        select(XpBoostEvent).order_by(XpBoostEvent.starts_at, XpBoostEvent.id)
    )).scalars().all()
    scope = (await db.execute(
        select(User.id, UserProfile.emby_user_id).join(UserProfile, UserProfile.user_id == User.id).where(LINKED_ACCOUNT)
    )).all()
    return Context(
        as_of=as_of or datetime.now(UTC),
        ledger_start=await _ledger_start(db),
        exclusions=tuple(await load_exclusion_entries(db)),
        events=tuple(
            BonusEvent(ev.id, ev.name, ev.multiplier, ev.starts_at, ev.ends_at, ev.action_filter, ev.enabled)
            for ev in events
        ),
        erased=await load_erased_identities(db),
        zone=await get_instance_zone(db),
        scope=dict(scope),
    )
