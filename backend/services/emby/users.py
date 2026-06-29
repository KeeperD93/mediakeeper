"""Emby user management — enable/disable accounts and revoke sessions.

Used by the Portal admin "Users" page to keep MediaKeeper as a single
pane of glass: when an admin flips the Emby toggle, the upstream policy
is patched and any in-flight session is logged out so the change is
felt immediately on the streaming side.
"""
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client

from .config import _get_emby_config

logger = logging.getLogger("mediakeeper.emby.users")


def _looks_like_email(value: str) -> bool:
    """Minimal sanity gate (not RFC validation): exactly one ``@``, a
    dotted domain, no whitespace, within the column width."""
    if not value or len(value) > 254 or value.count("@") != 1:
        return False
    if any(ch.isspace() for ch in value):
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def email_from_emby_user(emby_user: dict[str, Any]) -> str | None:
    """Best-effort email for an Emby account.

    Emby has no standalone email field — an address only exists once the
    account is linked to Emby Connect, where it surfaces as
    ``ConnectUserName``. That field historically also carried a plain
    Connect username, so we keep the value only when it actually looks
    like an email."""
    raw = (emby_user.get("ConnectUserName") or "").strip()
    return raw if _looks_like_email(raw) else None


async def list_emby_users(db: AsyncSession) -> list[dict[str, Any]]:
    """Return the raw Emby ``/Users`` payload, or ``[]`` if not configured."""
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, api_key = cfg
    try:
        client = get_internal_client()
        res = await client.get(f"{url}/Users", headers={"X-Emby-Token": api_key})
        if res.status_code != 200:
            logger.warning("list_emby_users: HTTP %s", res.status_code)
            return []
        return res.json() or []
    except Exception as e:
        logger.error("list_emby_users error: %s", e)
        return []


async def get_emby_user(db: AsyncSession, emby_user_id: str) -> dict[str, Any] | None:
    """Fetch a single Emby user (full payload incl. ``Policy``)."""
    cfg = await _get_emby_config(db)
    if not cfg or not emby_user_id:
        return None
    url, api_key = cfg
    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Users/{emby_user_id}",
            headers={"X-Emby-Token": api_key},
        )
        if res.status_code != 200:
            return None
        return res.json()
    except Exception as e:
        logger.error("get_emby_user error: %s", e)
        return None


async def set_emby_user_enabled(
    db: AsyncSession, emby_user_id: str, *, enabled: bool
) -> dict[str, Any]:
    """Toggle ``Policy.IsDisabled`` on the Emby account.

    Returns ``{"ok": True}`` on success, ``{"error": "..."}`` otherwise.
    When ``enabled=False`` we also try to log out every active session
    so the change is enforced instantly on the user's clients.
    """
    cfg = await _get_emby_config(db)
    if not cfg:
        logger.warning("set_emby_user_enabled: no Emby source configured")
        return {"error": "no_source"}
    if not emby_user_id:
        logger.warning("set_emby_user_enabled: empty emby_user_id")
        return {"error": "no_emby_id"}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key, "Content-Type": "application/json"}

    user = await get_emby_user(db, emby_user_id)
    if not user:
        logger.warning(
            "set_emby_user_enabled: GET /Users/%s returned no payload (404 or network)",
            emby_user_id,
        )
        return {"error": "user_not_found"}

    policy = dict(user.get("Policy") or {})
    if not policy:
        logger.warning(
            "set_emby_user_enabled: Emby returned a user without Policy "
            "(api key may lack admin rights) — id=%s",
            emby_user_id,
        )
        return {"error": "no_policy"}
    policy["IsDisabled"] = not enabled

    try:
        client = get_internal_client()
        res = await client.post(
            f"{url}/Users/{emby_user_id}/Policy",
            headers=headers,
            json=policy,
        )
        if res.status_code not in (200, 204):
            # Emby usually returns 401/403 when the api_key isn't admin,
            # 400 when the payload is malformed, 500 on internal issues.
            body_preview = ""
            try:
                body_preview = (res.text or "")[:300]
            except Exception:
                body_preview = ""
            logger.warning(
                "set_emby_user_enabled: HTTP %s — emby_id=%s, body=%s",
                res.status_code, emby_user_id, body_preview,
            )
            return {"error": f"http_{res.status_code}"}
    except Exception as e:
        logger.error(
            "set_emby_user_enabled network error: emby_id=%s err=%s",
            emby_user_id, e,
        )
        return {"error": "network"}

    if not enabled:
        await _kill_sessions_for_user(url, api_key, emby_user_id)

    return {"ok": True}


async def _kill_sessions_for_user(url: str, api_key: str, emby_user_id: str) -> None:
    """Best-effort logout of every active session for the given Emby user.

    Emby returns sessions through ``/Sessions``; we filter by ``UserId``
    and POST ``/Sessions/{id}/Logout`` for each. Failures are swallowed
    because the policy update already enforces the disable on the next
    auth check — the logout is just a faster cut-off.
    """
    client = get_internal_client()
    headers = {"X-Emby-Token": api_key}
    try:
        res = await client.get(f"{url}/Sessions", headers=headers)
        if res.status_code != 200:
            return
        sessions = res.json() or []
    except Exception:
        return

    for session in sessions:
        if session.get("UserId") != emby_user_id:
            continue
        session_id = session.get("Id")
        if not session_id:
            continue
        try:
            await client.post(
                f"{url}/Sessions/{session_id}/Logout",
                headers=headers,
            )
        except Exception:  # noqa: S112 -- intentional best-effort iteration, skip individual failure
            continue
