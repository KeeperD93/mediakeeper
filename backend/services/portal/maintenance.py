"""Portal maintenance mode (settings-backed read/write helpers).

Three rows in the generic ``settings`` table back the feature:

* ``maintenance.enabled`` — ``"true"``/``"false"`` flag.
* ``maintenance.text_fr`` / ``maintenance.text_en`` — admin-supplied
  texts displayed on the public holding page. Seeded with sensible
  defaults by migration 045.

The router guard on the SPA checks ``is_maintenance_enabled`` before
every navigation; ``get_maintenance_text`` resolves the locale-specific
string from an ``Accept-Language`` hint, defaulting to French.
"""
from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.settings import Setting

logger = logging.getLogger("mediakeeper.portal.maintenance")


MAINTENANCE_KEYS = (
    "maintenance.enabled",
    "maintenance.text_fr",
    "maintenance.text_en",
)

_DEFAULT_TEXT_FR = (
    "Le site est actuellement en maintenance, "
    "merci de votre compréhension."
)
_DEFAULT_TEXT_EN = (
    "The site is currently under maintenance, "
    "thanks for your understanding."
)


def _parse_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


async def _read_all(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(
        select(Setting).where(Setting.key.in_(MAINTENANCE_KEYS))
    )).scalars().all()
    return {r.key: (r.value or "") for r in rows}


async def is_maintenance_enabled(db: AsyncSession) -> bool:
    row = (await db.execute(
        select(Setting).where(Setting.key == "maintenance.enabled")
    )).scalar_one_or_none()
    return _parse_bool(row.value if row else None)


async def get_maintenance_text(db: AsyncSession, lang: str) -> str:
    """Resolve the maintenance text for the requested locale.

    ``lang`` is matched permissively: anything starting with ``en``
    (case-insensitive) returns the English string, everything else
    falls back to French. Missing rows fall through to seeded defaults.
    """
    stored = await _read_all(db)
    is_en = (lang or "").lower().startswith("en")
    if is_en:
        return stored.get("maintenance.text_en") or _DEFAULT_TEXT_EN
    return stored.get("maintenance.text_fr") or _DEFAULT_TEXT_FR


async def get_maintenance_state(db: AsyncSession, lang: str) -> dict:
    """Combine ``enabled`` + locale-resolved ``text`` for the public route."""
    return {
        "enabled": await is_maintenance_enabled(db),
        "text": await get_maintenance_text(db, lang),
    }


async def get_maintenance_admin_settings(db: AsyncSession) -> dict:
    """Admin payload: full FR/EN text + enabled flag, no resolution."""
    stored = await _read_all(db)
    return {
        "enabled": _parse_bool(stored.get("maintenance.enabled")),
        "text_fr": stored.get("maintenance.text_fr") or _DEFAULT_TEXT_FR,
        "text_en": stored.get("maintenance.text_en") or _DEFAULT_TEXT_EN,
    }


async def update_maintenance_settings(
    db: AsyncSession,
    *,
    enabled: bool | None = None,
    text_fr: str | None = None,
    text_en: str | None = None,
) -> dict:
    """Upsert any subset of maintenance settings. Returns the refreshed dict."""
    updates: dict[str, str] = {}
    if enabled is not None:
        updates["maintenance.enabled"] = "true" if enabled else "false"
    if text_fr is not None:
        updates["maintenance.text_fr"] = text_fr.strip()
    if text_en is not None:
        updates["maintenance.text_en"] = text_en.strip()

    for key, val in updates.items():
        row = (await db.execute(
            select(Setting).where(Setting.key == key)
        )).scalar_one_or_none()
        if row:
            row.value = val
        else:
            db.add(Setting(key=key, value=val))
    if updates:
        await db.commit()
        logger.info(f"[MAINTENANCE] updated keys={list(updates.keys())}")
    return await get_maintenance_admin_settings(db)
