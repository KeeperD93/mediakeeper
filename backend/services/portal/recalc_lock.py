"""One admin recalculation of the players' data at a time, whichever it is: the time zone
correction or the watch XP recalculation. One web process serves the admin, so a lock
of that process suffices; a second apply waits for nothing, it is refused."""
import asyncio

RECALC_LOCK = asyncio.Lock()
