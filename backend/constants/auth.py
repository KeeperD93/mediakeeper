"""Session cookie names shared by the auth routes, the CSRF middleware and the
rate-limit keys.

Kept out of ``api.auth`` so ``core`` modules can read them without importing
the auth routers, which import ``core`` back.
"""
from typing import Final

__all__ = [
    "COOKIE_NAME",
    "CSRF_COOKIE_NAME",
    "PORTAL_COOKIE_NAME",
]

#: Admin (backoffice) JWT cookie.
COOKIE_NAME: Final[str] = "mk_token"
#: The portal uses a distinct cookie so an Emby-authenticated user can never
#: reach the backoffice, even if rq_token leaks.
PORTAL_COOKIE_NAME: Final[str] = "rq_token"
#: Double-submit CSRF token: readable by the SPA, which echoes it in X-CSRF-Token.
CSRF_COOKIE_NAME: Final[str] = "mk_csrf"
