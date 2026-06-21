"""HealthCheck result queries (list, detail, grouped)."""
import json

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import decode_cursor, encode_cursor
from models.healthcheck import HealthCheckResult

from ._analyze import _severity_rank_expr


def _row_to_item(r, severity_rank_value=None) -> dict | None:
    try:
        issues = json.loads(r.issues) if r.issues else []
    except Exception:
        issues = []
    # Filter out the legacy "no_subtitles" type — now handled by the subtitles module.
    issues = [i for i in issues if i.get("type") != "no_subtitles"]
    if not issues:
        return None

    item = {
        "id": r.id,
        "item_id": r.item_id,
        "item_name": r.item_name,
        "item_type": r.item_type,
        "series_id": getattr(r, "series_id", None),
        "series_name": r.series_name,
        "season_num": getattr(r, "season_num", None),
        "episode_num": getattr(r, "episode_num", None),
        "library": r.library_name,
        "severity": r.severity,
        "issues": issues,
    }
    if hasattr(r, "file_path"):
        item["file_path"] = r.file_path
    if hasattr(r, "scanned_at") and r.scanned_at is not None:
        item["scanned_at"] = r.scanned_at.isoformat()
    if severity_rank_value is not None:
        item["_severity_rank"] = severity_rank_value
    return item


async def get_healthcheck_issues(
    db: AsyncSession,
    cursor: str = "",
    limit: int = 50,
    severity: str = "",
    library: str = "",
    issue_type: str = "",
    extension: str = "",
) -> dict:
    """Return the paginated issues (cursor-based)."""
    severity_rank = _severity_rank_expr()
    query = select(HealthCheckResult, severity_rank.label("severity_rank")).order_by(
        severity_rank,
        HealthCheckResult.id.desc(),
    )

    if severity:
        query = query.where(HealthCheckResult.severity == severity)
    if library:
        query = query.where(HealthCheckResult.library_name == library)
    if issue_type:
        query = query.where(HealthCheckResult.issues.contains(f'"type": "{issue_type}"', autoescape=True))
    if extension:
        query = query.where(HealthCheckResult.file_path.iendswith(f".{extension}", autoescape=True))

    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    decoded = decode_cursor(cursor, int_fields=("id", "severity_rank"))
    if decoded and "id" in decoded and "severity_rank" in decoded:
        query = query.where(
            or_(
                severity_rank > decoded["severity_rank"],
                and_(
                    severity_rank == decoded["severity_rank"],
                    HealthCheckResult.id < decoded["id"],
                ),
            )
        )

    result = await db.execute(query.limit(limit + 1))
    rows = result.all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for r, severity_rank_value in rows:
        item = _row_to_item(r, severity_rank_value)
        if item is not None:
            items.append(item)

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({
            "severity_rank": last["_severity_rank"],
            "id": last["id"],
        })

    for item in items:
        item.pop("_severity_rank", None)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


async def get_healthcheck_poster_details(
    db: AsyncSession, kind: str, key: str,
) -> dict:
    """
    Return le detail full d'un poster (series ou film).
    kind: "series" | "movie"
    key:  series_id for une series, item_id for un film
    """
    if kind == "series":
        q = select(HealthCheckResult).where(
            or_(
                HealthCheckResult.series_id == key,
                HealthCheckResult.series_name == key,
            )
        )
    else:
        q = select(HealthCheckResult).where(HealthCheckResult.item_id == key)
    res = await db.execute(q)
    rows = res.scalars().all()

    items = []
    for r in rows:
        item = _row_to_item(r)
        if item is not None:
            items.append(item)
    return {"items": items}


async def get_healthcheck_grouped(
    db: AsyncSession,
    severity: str | None = None,
    library: str | None = None,
    issue_type: str | None = None,
    extension: str | None = None,
) -> list[dict]:
    """
    Return ALL results grouped by poster (series via series_id, movie via item_id),
    with the exact total of issues and the worst severity. Not paginated.
    """
    SEV_RANK = {"critical": 3, "warning": 2, "info": 1, "ok": 0}

    q = select(
        HealthCheckResult.id,
        HealthCheckResult.item_id,
        HealthCheckResult.item_name,
        HealthCheckResult.item_type,
        HealthCheckResult.series_id,
        HealthCheckResult.series_name,
        HealthCheckResult.library_name,
        HealthCheckResult.issues,
        HealthCheckResult.severity,
    )
    if severity:
        q = q.where(HealthCheckResult.severity == severity)
    if library:
        q = q.where(HealthCheckResult.library_name == library)
    if extension:
        q = q.where(HealthCheckResult.file_path.iendswith(f".{extension}", autoescape=True))
    res = await db.execute(q)
    rows = res.all()

    groups: dict[str, dict] = {}
    for r in rows:
        try:
            issues = json.loads(r.issues) if r.issues else []
        except Exception:
            issues = []
        issues = [i for i in issues if i.get("type") != "no_subtitles"]
        if issue_type:
            issues = [i for i in issues if i.get("type") == issue_type]
        if not issues:
            continue
        issue_count = len(issues)

        if r.series_name:
            key = f"s:{r.series_id or r.series_name}"
            poster_item_id = r.series_id or r.item_id
            title = r.series_name
            is_series = True
        else:
            key = f"m:{r.item_id}"
            poster_item_id = r.item_id
            title = r.item_name
            is_series = False

        g = groups.get(key)
        if g is None:
            groups[key] = {
                "key": key,
                "item_id": poster_item_id,
                "title": title,
                "library": r.library_name,
                "severity": r.severity,
                "issue_count": issue_count,
                "episode_count": 1 if is_series else 0,
                "is_series": is_series,
            }
        else:
            g["issue_count"] += issue_count
            if is_series:
                g["episode_count"] += 1
            if (SEV_RANK.get(r.severity, 0)) > (SEV_RANK.get(g["severity"], 0)):
                g["severity"] = r.severity
            if r.series_id and g["item_id"] != r.series_id:
                g["item_id"] = r.series_id

    def sort_key(g):
        return (-SEV_RANK.get(g["severity"], 0), -g["issue_count"], g["title"].lower())

    return sorted(groups.values(), key=sort_key)
