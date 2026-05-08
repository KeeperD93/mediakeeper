"""Tiny helpers shared by the ``portal_admin_users*`` routers.

Extracted into its own module so each router file stays under the
300-line cap. Nothing project-wide here — strictly request-scoped
utilities used by every endpoint of the premium "Users" page.
"""
import csv
import io
import json as _json

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.csv_safe import safe_csv_row
from core.proxy import get_client_ip
from services.portal.admin_users import get_admin_user


def client_ip(request: Request) -> str | None:
    ip = get_client_ip(request)
    return ip[:64] if ip else None


def client_ua(request: Request) -> str | None:
    return request.headers.get("User-Agent")


async def resolve_profile(profile_id: int, db: AsyncSession):
    pair = await get_admin_user(db, profile_id)
    if not pair:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return pair


def rgpd_export_to_csv(payload: dict, profile_id: int) -> StreamingResponse:
    """Flatten the RGPD export dict into a key/value CSV.

    Heavy nested keys (lists, dicts) are JSON-serialised inline so the
    admin can open the file in any spreadsheet tool. Cells are passed
    through ``safe_csv_row`` to neutralise formula injection.
    """
    flat: list[tuple[str, str]] = []

    def _walk(prefix: str, value):
        if isinstance(value, dict):
            for k, v in value.items():
                _walk(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(value, list):
            flat.append((prefix, _json.dumps(value, ensure_ascii=False)))
        else:
            flat.append((prefix, "" if value is None else str(value)))

    _walk("", payload)
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["field", "value"])
    for k, v in flat:
        writer.writerow(safe_csv_row([k, v]))
    buf.seek(0)
    filename = f"mk-user-{profile_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
