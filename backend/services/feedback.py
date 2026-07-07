"""Bug/suggestion feedback: config, Discord relay, and the delegate moderation queue.

An admin sets a Discord webhook ("link code") + a pseudo (cycle 1); their own
reports relay straight to that webhook, pre-formatted as the tracker's
``=== BUG === … === END ===`` import block. Delegated portal users file reports
that are stored ``pending`` (cycle 3b) for the admin to edit / validate (relay)
/ reject on the tracker page; rejected reports are purged after a tunable
retention window (cycle 3c).
"""
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.feedback import (
    FEEDBACK_PLATFORMS,
    MAX_LOCATION,
    MAX_PSEUDO,
    MAX_REPRODUCTION,
    MAX_RESOLUTION,
    MAX_TAG_LEN,
    MAX_TAGS,
    MAX_TITLE,
    PLATFORM_BOTH,
    RETENTION_DEFAULT_DAYS,
    RETENTION_MAX_DAYS,
    RETENTION_MIN_DAYS,
    STATUS_PENDING,
    STATUS_REJECTED,
    TYPE_BUG,
    TYPE_SUGGESTION,
)
from core.url_safety import is_discord_webhook_url
from services.discord import send_discord_webhook
from services.settings import get_settings_map, set_settings_map

# Re-exported for the API layer (api/feedback.py, api/portal/feedback.py).
PLATFORMS = FEEDBACK_PLATFORMS

# The ``.webhook_url`` suffix makes core.encryption treat the value as
# sensitive → encrypted at rest transparently by the _kv layer.
KEY_ENABLED = "bug_report.enabled"
KEY_PSEUDO = "bug_report.discord_pseudo"
KEY_WEBHOOK = "bug_report.webhook_url"
KEY_RETENTION = "bug_report.reject_retention_days"
_CONFIG_KEYS = [KEY_ENABLED, KEY_PSEUDO, KEY_WEBHOOK, KEY_RETENTION]

# Discord caps a webhook message at 2000 chars; the block is wrapped in a ``` fence
# (8 chars), so the block itself must stay under this.
_MAX_BLOCK = 1990
# The composed "Signalé par" author ("<reporter> (via <admin>)") holds two pseudos.
_CAP_AUTHOR = 2 * MAX_PSEUDO + 8
# Transient status held while a report is relayed, so two concurrent validate
# calls can't both send the same report (see validate_feedback_report).
_STATUS_SENDING = "sending"


def _coerce_retention(raw) -> int:
    """Parse the stored retention setting, clamping to a sane day range."""
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return RETENTION_DEFAULT_DAYS
    return min(max(days, RETENTION_MIN_DAYS), RETENTION_MAX_DAYS)


async def get_feedback_config(db: AsyncSession) -> dict:
    v = await get_settings_map(db, _CONFIG_KEYS)
    return {
        "enabled": v.get(KEY_ENABLED) == "true",
        "discord_pseudo": v.get(KEY_PSEUDO, ""),
        "webhook_url": v.get(KEY_WEBHOOK, ""),
        "reject_retention_days": _coerce_retention(v.get(KEY_RETENTION)),
    }


async def save_feedback_config(
    db: AsyncSession,
    *,
    enabled: bool | None = None,
    discord_pseudo: str | None = None,
    webhook_url: str | None = None,
    retention_days: int | None = None,
) -> None:
    """Persist the feedback config. ``webhook_url`` is validated as a Discord
    webhook here too (defence in depth — the HTTP layer checks it first)."""
    if webhook_url and not is_discord_webhook_url(webhook_url.strip()):
        raise ValueError("invalid_webhook")
    updates: dict[str, str] = {}
    if enabled is not None:
        updates[KEY_ENABLED] = "true" if enabled else "false"
    if discord_pseudo is not None:
        updates[KEY_PSEUDO] = discord_pseudo.strip()[:MAX_PSEUDO]
    if webhook_url is not None:
        updates[KEY_WEBHOOK] = webhook_url.strip()
    if retention_days is not None:
        updates[KEY_RETENTION] = str(_coerce_retention(retention_days))
    if updates:
        await set_settings_map(db, updates)


def _defuse(value: str) -> str:
    """Break any ``===`` run so user text can't forge block delimiters/fields."""
    return (value or "").replace("===", "= = =")


def _oneline(value: str) -> str:
    """Single-line field: defuse delimiters + collapse newlines."""
    return _defuse(value).replace("\r", " ").replace("\n", " ").strip()


def _clip(value: str, cap: int) -> str:
    """Bound a rendered field to ``cap`` chars, appending ``…`` when content was
    actually dropped — so truncation is never silent (unlike a bare slice)."""
    return value if len(value) <= cap else value[: max(0, cap - 1)].rstrip() + "…"


def _report_author(fields: dict, admin_pseudo: str) -> str:
    """Resolve the 'Signalé par' identity for the relayed block.

    A delegate's report carries ``reporter_name`` → ``"<name> (via <admin>)"``,
    or ``"Anonyme (via <admin>)"`` when they opted out of showing their name, so
    the maintainer sees who reported it and via which instance. The admin's own
    direct reports carry no ``reporter_name`` → just the admin pseudo (empty ⇒
    anonymous).
    """
    admin = (admin_pseudo or "").strip()[:MAX_PSEUDO]
    reporter = (fields.get("reporter_name") or "").strip()[:MAX_PSEUDO]
    if reporter:
        name = "Anonyme" if fields.get("anonymous") else reporter
        return f"{name} (via {admin})" if admin else name
    return "" if fields.get("anonymous") else admin


def build_report_block(fields: dict, author: str) -> str:
    """Render the tracker-parsable block. ``author`` is the composed 'Signalé par'
    identity (empty ⇒ Anonyme). Every field is defused + length-bounded so the
    block can neither breach Discord's cap nor forge a delimiter."""
    from api.changelog import APP_VERSION  # lazy: avoids an api→services cycle

    platform = fields.get("platform")
    if platform not in PLATFORMS:
        platform = PLATFORM_BOTH
    head = (
        "=== BUG ===\n"
        f"TITRE: {_clip(_oneline(fields.get('title', '')), MAX_TITLE)}\n"
        f"ZONE: {_clip(_oneline(fields.get('zone', '')), MAX_LOCATION) or '-'}\n"
        f"MODULE: {_clip(_oneline(fields.get('module', '')), MAX_LOCATION) or '-'}\n"
        f"ONGLET: {_clip(_oneline(fields.get('tab', '')), MAX_LOCATION) or '-'}\n"
        f"PLATEFORME: {platform}\n"
        "DESCRIPTION:\n"
    )

    extras: list[str] = []
    repro = _clip(_defuse(fields.get("reproduction", "")).strip(), MAX_REPRODUCTION)
    if repro:
        extras.append(f"Reproduction: {repro}")
    resolution = _clip(_oneline(fields.get("resolution", "")), MAX_RESOLUTION)
    if resolution:
        extras.append(f"Résolution: {resolution}")
    kind = "Suggestion" if fields.get("type") == TYPE_SUGGESTION else "Bug"
    tags = [s for s in (_oneline(t)[:MAX_TAG_LEN] for t in fields.get("tags", [])) if s]
    extras.append(f"Type: {kind}" + (f" · Étiquettes: {', '.join(tags)}" if tags else ""))
    who = _clip(_oneline(author), _CAP_AUTHOR) or "Anonyme"
    extras.append(f"Signalé par: {who} · MediaKeeper {APP_VERSION}")
    tail = "\n\n" + "\n".join(extras) + "\n=== END ==="

    description = _defuse(fields.get("description", "")).strip()
    budget = _MAX_BLOCK - len(head) - len(tail)
    if len(description) > budget:
        description = description[: max(0, budget - 1)].rstrip() + "…"
    return head + description + tail


async def send_feedback_report(db: AsyncSession, fields: dict) -> bool:
    cfg = await get_feedback_config(db)
    if not cfg["enabled"] or not cfg["webhook_url"]:
        return False
    author = _report_author(fields, cfg["discord_pseudo"])
    payload = {
        "username": "MediaKeeper",
        "content": f"```\n{build_report_block(fields, author)}\n```",
        "allowed_mentions": {"parse": []},  # never resolve @everyone/@here/@user
        "flags": 4,                          # SUPPRESS_EMBEDS: no link/image preview
    }
    return await send_discord_webhook(cfg["webhook_url"], payload)


async def send_feedback_handshake(webhook_url: str) -> bool:
    """Test ping the maintainer watches for when a contributor links up."""
    payload = {
        "username": "MediaKeeper",
        "content": "MediaKeeper — liaison feedback confirmée.",
        "allowed_mentions": {"parse": []},
    }
    return await send_discord_webhook(webhook_url, payload)


async def create_pending_report(
    db: AsyncSession,
    *,
    reporter_user_id: int | None,
    reporter_name: str | None,
    fields: dict,
) -> None:
    """Store a delegated portal user's report as ``pending`` for admin review."""
    from models.portal.feedback_report import FeedbackReport  # lazy: avoid cycles

    platform = fields.get("platform")
    if platform not in PLATFORMS:
        platform = PLATFORM_BOTH
    db.add(
        FeedbackReport(
            reporter_user_id=reporter_user_id,
            reporter_name=(reporter_name or "").strip()[:MAX_PSEUDO] or None,
            type=TYPE_SUGGESTION if fields.get("type") == TYPE_SUGGESTION else TYPE_BUG,
            title=(fields.get("title") or "")[:200],
            description=fields.get("description") or "",
            reproduction=(fields.get("reproduction") or "").strip() or None,
            zone=(fields.get("zone") or "").strip() or None,
            module=(fields.get("module") or "").strip() or None,
            tab=(fields.get("tab") or "").strip() or None,
            platform=platform,
            resolution=(fields.get("resolution") or "").strip() or None,
            tags=[str(t)[:MAX_TAG_LEN] for t in (fields.get("tags") or [])][:MAX_TAGS],
            anonymous=bool(fields.get("anonymous")),
            status=STATUS_PENDING,
        )
    )
    await db.commit()


def _serialize_report(row) -> dict:
    return {
        "id": row.id,
        "reporter_name": row.reporter_name,
        "type": row.type,
        "title": row.title,
        "description": row.description,
        "reproduction": row.reproduction,
        "zone": row.zone,
        "module": row.module,
        "tab": row.tab,
        "platform": row.platform,
        "resolution": row.resolution,
        "tags": row.tags or [],
        "anonymous": bool(row.anonymous),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def list_feedback_reports(db: AsyncSession, status: str = STATUS_PENDING) -> list[dict]:
    from models.portal.feedback_report import FeedbackReport

    stmt = (
        select(FeedbackReport)
        .where(FeedbackReport.status == status)
        .order_by(FeedbackReport.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_report(r) for r in rows]


# Columns an admin may edit on a pending report (mirrors FeedbackReportUpdate).
_EDITABLE_FIELDS = frozenset(
    {
        "type", "title", "description", "reproduction", "zone",
        "module", "tab", "platform", "resolution", "tags",
    }
)


async def update_feedback_report(db: AsyncSession, report_id: int, updates: dict) -> bool:
    """Edit a pending report in place. False if missing or already handled.

    Only whitelisted columns are written — a defence-in-depth backstop should a
    caller ever reach this with keys the Pydantic schema didn't vet."""
    from models.portal.feedback_report import FeedbackReport

    row = await db.get(FeedbackReport, report_id)
    if row is None or row.status != STATUS_PENDING:
        return False
    for key, value in updates.items():
        if key in _EDITABLE_FIELDS:
            setattr(row, key, value)
    await db.commit()
    return True


async def _release_claim(db: AsyncSession, report_id: int) -> None:
    """Revert a ``sending`` claim back to ``pending`` after a failed relay."""
    from models.portal.feedback_report import FeedbackReport

    await db.execute(
        update(FeedbackReport)
        .where(FeedbackReport.id == report_id, FeedbackReport.status == _STATUS_SENDING)
        .values(status=STATUS_PENDING)
    )
    await db.commit()


async def validate_feedback_report(db: AsyncSession, report_id: int) -> str:
    """Relay a pending report to Discord then delete it. Returns a status token:
    ``sent`` | ``not_found`` | ``not_configured`` | ``send_failed``.

    The atomic pending→sending→(deleted|pending) claim makes two concurrent
    validate calls mutually exclusive, so the same report can never be relayed
    twice (only the winner's UPDATE matches a row)."""
    from models.portal.feedback_report import FeedbackReport

    claim = await db.execute(
        update(FeedbackReport)
        .where(FeedbackReport.id == report_id, FeedbackReport.status == STATUS_PENDING)
        .values(status=_STATUS_SENDING)
    )
    if (claim.rowcount or 0) != 1:
        await db.rollback()
        return "not_found"
    await db.commit()

    cfg = await get_feedback_config(db)
    if not cfg["enabled"] or not cfg["webhook_url"]:
        await _release_claim(db, report_id)
        return "not_configured"

    row = await db.get(FeedbackReport, report_id)
    fields = {
        "type": row.type,
        "title": row.title,
        "description": row.description,
        "reproduction": row.reproduction or "",
        "zone": row.zone or "",
        "module": row.module or "",
        "tab": row.tab or "",
        "platform": row.platform or PLATFORM_BOTH,
        "resolution": row.resolution or "",
        "tags": row.tags or [],
        "anonymous": bool(row.anonymous),
        "reporter_name": row.reporter_name,
    }
    if not await send_feedback_report(db, fields):
        await _release_claim(db, report_id)
        return "send_failed"
    await db.execute(delete(FeedbackReport).where(FeedbackReport.id == report_id))
    await db.commit()
    return "sent"


async def reject_feedback_report(db: AsyncSession, report_id: int) -> bool:
    """Mark a pending report rejected (kept for the retention window). False if
    missing or already handled — the atomic guard also serialises concurrent calls."""
    from datetime import datetime, timezone

    from models.portal.feedback_report import FeedbackReport

    result = await db.execute(
        update(FeedbackReport)
        .where(FeedbackReport.id == report_id, FeedbackReport.status == STATUS_PENDING)
        .values(status=STATUS_REJECTED, rejected_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return (result.rowcount or 0) == 1


async def purge_rejected_reports(db: AsyncSession, older_than_days: int = RETENTION_DEFAULT_DAYS) -> int:
    """Hard-delete rejected reports past the retention window. Returns the count."""
    from datetime import datetime, timedelta, timezone

    from models.portal.feedback_report import FeedbackReport

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    stmt = delete(FeedbackReport).where(
        FeedbackReport.status == STATUS_REJECTED, FeedbackReport.rejected_at < cutoff
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0
