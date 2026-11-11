"""Session cookie names shared by the auth routes, the CSRF middleware and the
rate-limit keys, and the session refusal codes shared by the admin and portal
auth dependencies, the admin sign-in and the image proxy.

Kept out of ``api.auth`` so ``core`` modules can read them without importing
the auth routers, which import ``core`` back.
"""
from typing import Final

__all__ = [
    "COOKIE_NAME",
    "CSRF_COOKIE_NAME",
    "PORTAL_COOKIE_NAME",
    "NOT_AUTHENTICATED",
    "TOKEN_INVALID",
    "USER_NOT_FOUND",
    "SESSION_REVOKED",
    "BACKOFFICE_FORBIDDEN",
    "MUST_CHANGE_PASSWORD",
]

#: Admin (backoffice) JWT cookie.
COOKIE_NAME: Final[str] = "mk_token"
#: The portal uses a distinct cookie so an Emby-authenticated user can never
#: reach the backoffice, even if rq_token leaks.
PORTAL_COOKIE_NAME: Final[str] = "rq_token"
#: Double-submit CSRF token: readable by the SPA, which echoes it in X-CSRF-Token.
CSRF_COOKIE_NAME: Final[str] = "mk_csrf"

#: Session refusals: the first four come with a 401 (no usable session), the
#: last two with a 403 (a valid session that may not go there).
NOT_AUTHENTICATED: Final[str] = "not_authenticated"
TOKEN_INVALID: Final[str] = "token_invalid"  # noqa: S105 -- refusal code, not a credential value
USER_NOT_FOUND: Final[str] = "user_not_found"
SESSION_REVOKED: Final[str] = "session_revoked"
BACKOFFICE_FORBIDDEN: Final[str] = "backoffice_forbidden"
MUST_CHANGE_PASSWORD: Final[str] = "must_change_password"  # noqa: S105 -- refusal code, not a credential value
