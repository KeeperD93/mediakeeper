"""Global HealthCheck summary: score, counters, last scan date."""
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.healthcheck import HealthCheckResult


async def get_healthcheck_summary(db: AsyncSession) -> dict:
    """Return the global summary: score, counters by severity and by type."""

    total_res = await db.execute(select(func.count(HealthCheckResult.id)))
    total_items = total_res.scalar() or 0

    severity_res = await db.execute(
        select(
            HealthCheckResult.severity,
            func.count(HealthCheckResult.id),
        ).group_by(HealthCheckResult.severity)
    )
    severity_counts = {row[0]: row[1] for row in severity_res.all()}

    critical = severity_counts.get("critical", 0)
    warning = severity_counts.get("warning", 0)
    info = severity_counts.get("info", 0)

    if total_items == 0:
        score = 100
    else:
        penalty = (critical * 10) + (warning * 3) + (info * 0.5)
        score = max(0, round(100 - penalty))

    all_res = await db.execute(select(HealthCheckResult.issues))
    type_counts: dict[str, int] = {}
    for (issues_json,) in all_res.all():
        try:
            for issue in json.loads(issues_json):
                t = issue.get("type", "unknown")
                if t == "no_subtitles":
                    continue  # handled by subtitles module
                type_counts[t] = type_counts.get(t, 0) + 1
        except Exception:
            pass

    ext_paths_res = await db.execute(
        select(HealthCheckResult.file_path).where(HealthCheckResult.file_path.isnot(None))
    )
    by_extension: dict[str, int] = {}
    for (fp,) in ext_paths_res.all():
        if fp and '.' in fp:
            ext = fp.rsplit('.', 1)[-1].lower().strip()
            if ext and len(ext) <= 6:
                by_extension[ext] = by_extension.get(ext, 0) + 1

    lib_res = await db.execute(
        select(
            HealthCheckResult.library_name,
            func.count(HealthCheckResult.id),
        ).group_by(HealthCheckResult.library_name)
    )
    by_library: dict[str, int] = {}
    for row in lib_res.all():
        name = row[0] or ""
        if name:
            by_library[name] = row[1]

    last_res = await db.execute(select(func.max(HealthCheckResult.scanned_at)))
    last_scan = last_res.scalar()

    return {
        "score": score,
        "total_issues": total_items,
        "critical": critical,
        "warning": warning,
        "info": info,
        "by_type": type_counts,
        "by_extension": by_extension,
        "by_library": by_library,
        "last_scan": last_scan.isoformat() if last_scan else None,
    }
