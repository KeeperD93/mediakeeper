"""
Service de management de l'history des teleloadings de sous-titres.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from models.subtitle_history import SubtitleDownload

logger = logging.getLogger("mediakeeper.subtitle_history")


def _download_to_dict(d: SubtitleDownload) -> dict:
    return {
        "id":                 d.id,
        "emby_item_id":       d.emby_item_id,
        "media_name":         d.media_name,
        "media_type":         d.media_type,
        "series_name":        d.series_name,
        "season":             d.season,
        "episode":            d.episode,
        "os_file_id":         d.os_file_id,
        "os_subtitle_id":     d.os_subtitle_id,
        "file_name":          d.file_name,
        "language":           d.language,
        "destination":        d.destination,
        "file_size":          d.file_size,
        "quality_score":      d.quality_score,
        "hash_match":         d.hash_match,
        "hearing_impaired":   d.hearing_impaired,
        "foreign_parts_only": d.foreign_parts_only,
        "from_trusted":       d.from_trusted,
        "ai_translated":      d.ai_translated,
        "source":             d.source,
        "downloaded_at":      d.downloaded_at.isoformat() if d.downloaded_at else None,
    }


async def record_download(db: AsyncSession, **kwargs) -> dict:
    dl = SubtitleDownload(**kwargs)
    db.add(dl)
    await db.commit()
    await db.refresh(dl)
    logger.info(
        "[HISTORY] Enregistre: %s [%s] score=%s source=%s",
        dl.media_name, dl.language, dl.quality_score, dl.source,
    )
    return _download_to_dict(dl)


async def get_history(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    item_id: str = "",
    language: str = "",
) -> dict:
    query = select(SubtitleDownload)

    if item_id:
        query = query.where(SubtitleDownload.emby_item_id == item_id)
    if language:
        query = query.where(SubtitleDownload.language == language)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated results
    query = query.order_by(desc(SubtitleDownload.downloaded_at))
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = [_download_to_dict(d) for d in result.scalars().all()]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_item_history(db: AsyncSession, emby_item_id: str) -> list[dict]:
    result = await db.execute(
        select(SubtitleDownload)
        .where(SubtitleDownload.emby_item_id == emby_item_id)
        .order_by(desc(SubtitleDownload.downloaded_at))
    )
    return [_download_to_dict(d) for d in result.scalars().all()]


async def get_latest_for_item(
    db: AsyncSession,
    emby_item_id: str,
    language: str,
) -> dict | None:
    result = await db.execute(
        select(SubtitleDownload)
        .where(
            SubtitleDownload.emby_item_id == emby_item_id,
            SubtitleDownload.language == language,
        )
        .order_by(desc(SubtitleDownload.downloaded_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return _download_to_dict(row) if row else None


async def get_statistics(db: AsyncSession) -> dict:
    """Statistiques des teleloadings de sous-titres."""
    from sqlalchemy import cast, Date
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Total downloads
    total_q = await db.execute(select(func.count()).select_from(SubtitleDownload))
    total_downloads = total_q.scalar() or 0

    # Downloads par langue
    lang_q = await db.execute(
        select(SubtitleDownload.language, func.count())
        .group_by(SubtitleDownload.language)
        .order_by(desc(func.count()))
    )
    by_language = {row[0]: row[1] for row in lang_q.all()}

    # Downloads par source
    source_q = await db.execute(
        select(SubtitleDownload.source, func.count())
        .group_by(SubtitleDownload.source)
    )
    by_source = {row[0]: row[1] for row in source_q.all()}

    # Downloads par jour (30 lasts jours)
    daily_q = await db.execute(
        select(
            cast(SubtitleDownload.downloaded_at, Date).label("day"),
            func.count(),
        )
        .where(SubtitleDownload.downloaded_at >= thirty_days_ago)
        .group_by("day")
        .order_by("day")
    )
    daily = {str(row[0]): row[1] for row in daily_q.all()}

    # Score moyen
    score_q = await db.execute(
        select(func.avg(SubtitleDownload.quality_score))
        .where(SubtitleDownload.quality_score.isnot(None))
    )
    avg_score = round(score_q.scalar() or 0, 1)

    # Distribution des scores (par tranche de 1)
    score_dist = {}
    for bucket in range(1, 6):
        sq = await db.execute(
            select(func.count()).select_from(SubtitleDownload)
            .where(
                SubtitleDownload.quality_score >= bucket,
                SubtitleDownload.quality_score < bucket + 1,
            )
        )
        score_dist[str(bucket)] = sq.scalar() or 0

    # Moyenne daily
    days_with_data = len(daily) or 1
    avg_daily = round(sum(daily.values()) / days_with_data, 1) if daily else 0

    return {
        "total_downloads": total_downloads,
        "by_language": by_language,
        "by_source": by_source,
        "daily": daily,
        "avg_score": avg_score,
        "score_distribution": score_dist,
        "avg_daily": avg_daily,
    }
