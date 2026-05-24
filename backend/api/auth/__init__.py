"""
/api/auth router — package split into modules (Rule 9, <= 300 lines).

Re-exports for compat history des imports `from api.auth import X`.
"""
from fastapi import APIRouter

from ._cookies import (
    COOKIE_NAME,
    PORTAL_COOKIE_NAME,
    _clear_jwt_cookie,
    _set_portal_jwt_cookie,
    _set_jwt_cookie,
)
from ._csrf import (
    CSRF_COOKIE_NAME,
    clear_csrf_cookie,
    ensure_csrf_cookie,
    require_csrf,
    rotate_csrf_cookie,
)
from ._portal import ensure_portal_admin_profile, grant_portal_admin_session
from ._deps import get_current_user
from .login import router as _login_router
from .profile import router as _profile_router

router = APIRouter(prefix="/api/auth", tags=["auth"])
router.include_router(_login_router)
router.include_router(_profile_router)

__all__ = [
    "COOKIE_NAME",
    "CSRF_COOKIE_NAME",
    "PORTAL_COOKIE_NAME",
    "_clear_jwt_cookie",
    "_set_portal_jwt_cookie",
    "_set_jwt_cookie",
    "clear_csrf_cookie",
    "ensure_portal_admin_profile",
    "ensure_csrf_cookie",
    "get_current_user",
    "grant_portal_admin_session",
    "require_csrf",
    "rotate_csrf_cookie",
    "router",
]
