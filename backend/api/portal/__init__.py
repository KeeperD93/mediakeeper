"""Portal API — all sub-routers assembled under /api/portal."""
from fastapi import APIRouter

from api.portal.auth import router as auth_router
from api.portal.profiles import router as profiles_router
from api.portal.profile_settings import (
    router as profile_settings_router,
    avatar_router as portal_avatar_router,
)
from api.portal.requests import router as requests_router
from api.portal.tickets import router as tickets_router
from api.portal.news import router as news_router
from api.portal.achievements import router as achievements_router
from api.portal.chat import router as chat_router
from api.portal.social import router as social_router
from api.portal.lists import router as lists_router
from api.portal.lists_admin import router as lists_admin_router
from api.portal.events import router as events_router
from api.portal.admin import router as admin_router
from api.portal.admin_debug import router as admin_debug_router
from api.portal.catalog import router as discover_router
from api.portal.library import router as available_router
from api.portal.activity import router as activity_router
from api.portal.top20 import router as top20_router
from api.portal.featured import router as featured_router
from api.portal.availability import router as availability_router
from api.portal.trailers import router as trailers_router
from api.portal.notifications import router as notifications_router
from api.portal.xp_events import router as xp_events_router
from api.portal.daily_digest import router as daily_digest_router
from api.portal.help import (
    router as help_router,
    admin_router as help_admin_router,
)

router = APIRouter(prefix="/api/portal")

router.include_router(auth_router)
router.include_router(profiles_router)
router.include_router(profile_settings_router)
router.include_router(portal_avatar_router)
router.include_router(requests_router)
router.include_router(tickets_router)
router.include_router(news_router)
router.include_router(achievements_router)
router.include_router(chat_router)
router.include_router(social_router)
router.include_router(lists_router)
router.include_router(lists_admin_router)
router.include_router(events_router)
router.include_router(admin_router)
router.include_router(admin_debug_router)
router.include_router(discover_router)
router.include_router(available_router)
router.include_router(activity_router)
router.include_router(top20_router)
router.include_router(featured_router)
router.include_router(availability_router)
router.include_router(trailers_router)
router.include_router(notifications_router)
router.include_router(xp_events_router)
router.include_router(daily_digest_router)
router.include_router(help_router)
router.include_router(help_admin_router)
