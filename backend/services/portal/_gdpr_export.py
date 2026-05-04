"""ZIP packaging for the GDPR opt-in export.

Lives in its own private module so ``gdpr.py`` stays under the 300-
line cap. The public entry point remains ``services.portal.gdpr.
build_export_zip`` (re-exported there).
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.user import User

from ._gdpr_collect import collect_full_user_data


# Hard cap on the export ZIP size. Anything past this is symptomatic of
# either runaway data growth or an attempted resource-exhaustion probe.
# 50 MB is generous for typical user histories (chat, ratings,
# achievements, login log) and small enough to fit a single HTTP
# response without streaming.
EXPORT_MAX_BYTES = 50 * 1024 * 1024


_README_TEMPLATE = """\
MediaKeeper — personal data export
==================================

Username : {username}
User ID  : {user_id}
Exported : {exported_at}

This archive contains every row stored in MediaKeeper that is bound to
your account. Each ``*.json`` file mirrors one source table.

Excluded on purpose:
  - admin_notes / tags         (admin curation, not your data)
  - third-party Emby data      (lives on the Emby server, not here)
  - request blacklist          (admin moderation tool)

Included tables ({table_count}):
{table_list}

Format: UTF-8 JSON, pretty-printed. Timestamps are ISO 8601 in UTC.

For questions, please contact the operator of this MediaKeeper instance.
"""


def _build_zip_bytes(payload: dict[str, Any]) -> bytes:
    """Pack one JSON file per table + a README into an in-memory ZIP.

    Raises :class:`OverflowError` once the cumulative compressed size
    exceeds :data:`EXPORT_MAX_BYTES` so the caller can answer 413.
    """
    metadata = payload.get("metadata", {})
    table_keys = [k for k in payload.keys() if k != "metadata"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = _README_TEMPLATE.format(
            username=metadata.get("username", ""),
            user_id=metadata.get("user_id", ""),
            exported_at=metadata.get("exported_at", ""),
            table_count=len(table_keys),
            table_list="\n".join(f"  - {k}.json" for k in table_keys),
        )
        zf.writestr("README.txt", readme)
        for key in table_keys:
            blob = json.dumps(
                payload[key], ensure_ascii=False, indent=2, default=str,
            )
            zf.writestr(f"{key}.json", blob)
            if buf.tell() > EXPORT_MAX_BYTES:
                raise OverflowError("export_too_large")
        zf.writestr(
            "metadata.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
        )
    data = buf.getvalue()
    if len(data) > EXPORT_MAX_BYTES:
        raise OverflowError("export_too_large")
    return data


async def build_export_zip(
    db: AsyncSession, user: User, profile: UserProfile,
) -> tuple[bytes, str]:
    """Return the ZIP bytes + a timestamped filename.

    The filename is ``mediakeeper-export-<username>-<YYYYMMDD>.zip``.
    """
    payload = await collect_full_user_data(db, user, profile)
    data = _build_zip_bytes(payload)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_username = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in (user.username or "user")
    )
    filename = f"mediakeeper-export-{safe_username}-{stamp}.zip"
    return data, filename
