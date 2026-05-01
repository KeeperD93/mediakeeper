"""Tiny helpers shared by the ``portal_admin_users*`` routers.

Extracted into its own module so each router file stays under the
300-line cap. Nothing project-wide here — strictly request-scoped
utilities used by every endpoint of the premium "Users" page.
"""
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from services.portal.admin_users import get_admin_user


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    return (request.client.host if request.client else None)


def client_ua(request: Request) -> str | None:
    return request.headers.get("User-Agent")


async def resolve_profile(profile_id: int, db: AsyncSession):
    pair = await get_admin_user(db, profile_id)
    if not pair:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return pair
