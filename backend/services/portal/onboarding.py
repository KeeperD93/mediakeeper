"""First-login wizard: everything the member chose is saved at once when they finish."""
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import display_name as dn
from models.portal.profile import UserProfile
from services.portal.display_name_rules import clean_display_name
from services.portal.profiles import update_profile


async def complete_onboarding(db: AsyncSession, user_id: int, choices: dict) -> UserProfile:
    """Save the wizard's choices (display name, language, visibility, genres) and mark
    it finished, in one transaction.

    The row is locked so a double submit saves once; a wizard already finished is
    left as it is. A refused name raises the save's own ``display_name_<verdict>``
    error and writes nothing, an empty one too: the wizard never ends without one.
    Choices left out of ``choices`` keep their stored value.
    """
    stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    bind = db.get_bind()
    if bind is not None and bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    profile = (await db.execute(
        stmt.execution_options(populate_existing=True)
    )).scalar_one()
    if profile.onboarding_completed_at is not None:
        # Nothing written: the commit only releases the lock and, unlike a
        # rollback, leaves the profile readable for the response.
        await db.commit()
        return profile
    if profile.forced_public and choices.get("is_public") is False:
        await db.rollback()
        raise HTTPException(status_code=403, detail="profile_visibility_locked")
    # The save skips a name that cleans down to nothing; here it would end the wizard.
    if not clean_display_name(choices.get("display_name")):
        await db.rollback()
        raise HTTPException(
            status_code=dn.REFUSAL_STATUS[dn.INVALID], detail=f"display_name_{dn.INVALID}",
        )
    profile.onboarding_completed_at = datetime.now(UTC)
    try:
        return await update_profile(db, profile, choices)
    except HTTPException:
        await db.rollback()
        raise
