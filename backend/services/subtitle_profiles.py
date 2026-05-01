"""
Service de management des profils de sous-titres.
"""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.subtitle_profile import SubtitleProfile

logger = logging.getLogger("mediakeeper.subtitle_profiles")


def _profile_to_dict(p: SubtitleProfile) -> dict:
    return {
        "id":               p.id,
        "name":             p.name,
        "is_default":       p.is_default,
        "languages":        json.loads(p.languages) if p.languages else [],
        "include_hi":       p.include_hi,
        "include_forced":   p.include_forced,
        "exclude_ai":       p.exclude_ai,
        "exclude_machine":  p.exclude_machine,
        "prefer_trusted":   p.prefer_trusted,
        "prefer_hash_match": p.prefer_hash_match,
        "auto_download":    p.auto_download,
        "min_score":        p.min_score,
        "created_at":       p.created_at.isoformat() if p.created_at else None,
        "updated_at":       p.updated_at.isoformat() if p.updated_at else None,
    }


async def get_profiles(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(SubtitleProfile).order_by(SubtitleProfile.name)
    )
    return [_profile_to_dict(p) for p in result.scalars().all()]


async def get_profile(db: AsyncSession, profile_id: int) -> dict | None:
    result = await db.execute(
        select(SubtitleProfile).where(SubtitleProfile.id == profile_id)
    )
    row = result.scalar_one_or_none()
    return _profile_to_dict(row) if row else None


async def get_default_profile(db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(SubtitleProfile).where(SubtitleProfile.is_default.is_(True))
    )
    row = result.scalar_one_or_none()
    return _profile_to_dict(row) if row else None


async def create_profile(db: AsyncSession, data: dict) -> dict:
    profile = SubtitleProfile(
        name=data["name"],
        languages=json.dumps(data.get("languages", ["fre", "eng"])),
        include_hi=data.get("include_hi", False),
        include_forced=data.get("include_forced", True),
        exclude_ai=data.get("exclude_ai", True),
        exclude_machine=data.get("exclude_machine", True),
        prefer_trusted=data.get("prefer_trusted", True),
        prefer_hash_match=data.get("prefer_hash_match", True),
        auto_download=data.get("auto_download", False),
        min_score=data.get("min_score", 3.0),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info(f"[PROFILES] Profil '{profile.name}' cree (id={profile.id})")
    return _profile_to_dict(profile)


async def update_profile(db: AsyncSession, profile_id: int, data: dict) -> dict | None:
    result = await db.execute(
        select(SubtitleProfile).where(SubtitleProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return None

    for field in ("name", "include_hi", "include_forced", "exclude_ai",
                  "exclude_machine", "prefer_trusted", "prefer_hash_match",
                  "auto_download", "min_score"):
        if field in data:
            setattr(profile, field, data[field])
    if "languages" in data:
        profile.languages = json.dumps(data["languages"])

    await db.commit()
    await db.refresh(profile)
    logger.info(f"[PROFILES] Profil '{profile.name}' mis a jour (id={profile.id})")
    return _profile_to_dict(profile)


async def delete_profile(db: AsyncSession, profile_id: int) -> bool:
    result = await db.execute(
        select(SubtitleProfile).where(SubtitleProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return False
    name = profile.name
    await db.delete(profile)
    await db.commit()
    logger.info(f"[PROFILES] Profil '{name}' delete (id={profile_id})")
    return True


async def get_default_profile_languages(db: AsyncSession) -> list[str] | None:
    """Return the languages of the default profile, or None if no profile exists."""
    p = await get_default_profile(db)
    if p and p.get("languages"):
        return p["languages"]
    return None


async def set_default_profile(db: AsyncSession, profile_id: int) -> dict | None:
    # Retirer le flag default de all les profils
    all_result = await db.execute(select(SubtitleProfile))
    for p in all_result.scalars().all():
        p.is_default = (p.id == profile_id)

    await db.commit()

    return await get_profile(db, profile_id)
