"""The ``secret_pilot`` trophy: the first viewer of a freshly added title."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.playback_overlap import _as_utc

# How recent an item must be (relative to its Emby ``DateCreated``) for the
# first-viewer claim to count. 30 days mirrors the "recently added" shelf
# surfaced on the portal home; revisit if live feedback shows the window is
# too lax or too strict.
PILOT_FRESHNESS_DAYS = 30


async def is_first_viewer_of_fresh_content(
    db: AsyncSession, emby_user_ids: list[str]
) -> bool:
    """``True`` iff the observed user opened a freshly-added item *before*
    any other user did.

    "Freshly added" is defined relative to ``EmbyTmdbIndex.date_created``
    (the cached Emby ``DateCreated`` timestamp): a session qualifies iff
    ``session.started_at - date_created <= PILOT_FRESHNESS_DAYS``. Items
    without a cached ``date_created`` are skipped — without the
    metadata we cannot prove the freshness claim, so they cannot fire
    the trophy. Timestamps are normalised to UTC via :func:`_as_utc`.

    The "first viewer" guard is a NOT-EXISTS subquery: for each
    candidate session of the observed user, we look for any session of
    *another* Emby user on the same item that started strictly before.
    A negative result on at least one candidate is enough to unlock.
    Anti-trivial guard (single-user instance) is enforced upstream by
    the caller, mirroring ``secret_sync``.
    """
    if not emby_user_ids:
        return False

    candidates = (await db.execute(
        select(
            PlaybackSession.item_id,
            PlaybackSession.started_at,
            EmbyTmdbIndex.date_created,
        )
        .select_from(PlaybackSession)
        .join(
            EmbyTmdbIndex,
            PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
        )
        .where(
            PlaybackSession.user_id.in_(emby_user_ids),
            EmbyTmdbIndex.date_created.isnot(None),
        )
    )).all()

    fresh_window = timedelta(days=PILOT_FRESHNESS_DAYS)
    for item_id, started_at, date_created in candidates:
        started = _as_utc(started_at)
        created = _as_utc(date_created)
        if started is None or created is None:
            continue
        if started - created > fresh_window or started < created:
            continue
        earlier = (await db.execute(
            select(PlaybackSession.id).where(
                PlaybackSession.item_id == item_id,
                PlaybackSession.user_id.notin_(emby_user_ids),
                PlaybackSession.started_at < started_at,
            ).limit(1)
        )).first()
        if earlier is None:
            return True
    return False
