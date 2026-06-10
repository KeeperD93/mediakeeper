"""
Cursor-based pagination — utilities.

Encoding: base64url(json({"id": <last_id>}))
Advantages over offset: no duplicates/skips during concurrent inserts/deletes.

API usage:
    ?cursor=<opaque>&limit=25
    -> returns { items, next_cursor, has_more, total }

Backwards compatibility: if `page` is given without `cursor`, we fall back to offset.
"""

import base64
import json
import logging
from typing import Optional

logger = logging.getLogger("mediakeeper.pagination")


def encode_cursor(data: dict) -> str:
    """Encode a dict as an opaque base64url cursor."""
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, int_fields: tuple[str, ...] = ("id",)) -> dict | None:
    """Decode an opaque cursor. Return None if invalid.

    `int_fields` are coerced to int: a forged non-integer value (e.g. ``{"id": "x"}``)
    would otherwise reach a ``WHERE col < <value>`` comparison and raise on
    PostgreSQL (``bigint < text``). SQLite coerces silently, so it must be rejected
    here rather than relying on the database.
    """
    if not cursor:
        return None
    try:
        # Re-pad base64
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        decoded = json.loads(raw)
    except Exception:
        logger.warning("Invalid cursor ignored: %s", cursor[:50])
        return None
    if not isinstance(decoded, dict):
        return None
    try:
        for field in int_fields:
            if field in decoded:
                decoded[field] = int(decoded[field])
    except (TypeError, ValueError):
        logger.warning("Cursor with non-integer pagination field ignored")
        return None
    return decoded


def build_cursor_response(
    items: list[dict],
    total: int,
    limit: int,
    cursor_field: str = "id",
    has_more: Optional[bool] = None,
) -> dict:
    """
    Build the cursor-based paginated response.

    items      : list of dicts already sorted/limited (limit+0, not limit+1)
    total      : total count (for info)
    limit      : requested page size
    cursor_field : key in each item used for the next cursor
    """
    if has_more is None:
        has_more = len(items) >= limit
    next_cursor = None

    if has_more and items:
        last = items[-1]
        val = last.get(cursor_field)
        if val is not None:
            next_cursor = encode_cursor({"id": val})

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
