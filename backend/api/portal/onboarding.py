"""First-login wizard endpoint: the member's choices, saved at once at the end."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from constants import display_name as dn
from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from models.portal.profile import UserProfile
from models.user import User
from services.portal import daily_digest as dd_svc
from services.portal.onboarding import complete_onboarding
from services.portal.profiles import serialize_profile_with_effective_lang

router = APIRouter(prefix="/profiles", tags=["portal-onboarding"])

# The genre picker offers 18 genres: the cap only bounds a forged payload.
_MAX_GENRES = 30


class OnboardingChoices(BaseModel):
    """The wizard's choices; one left out keeps its stored value, as on PUT /me."""
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(..., min_length=1, max_length=dn.MAX_LENGTH)
    # None follows the instance default, as « Default » does in the settings.
    language: Literal["fr", "en"] | None = None
    is_public: bool
    favorite_genres: list[Annotated[int, Field(gt=0)]] | None = Field(
        None, max_length=_MAX_GENRES,
    )


@router.post("/me/onboarding")
@limiter.limit("10/minute", key_func=portal_user_or_ip_key)
async def finish_onboarding(
    request: Request,
    choices: OnboardingChoices,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Save the wizard's choices and mark it finished (``complete_onboarding``).
    Every cached digest is rebuilt: the member's greets them by the name they just
    chose, the others' podiums show that name, or drop a profile turned private."""
    user, _ = up
    profile = await complete_onboarding(db, user.id, choices.model_dump(exclude_unset=True))
    dd_svc.clear_cache()
    return await serialize_profile_with_effective_lang(db, profile, user=user)
