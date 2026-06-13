"""Single source of truth for parsing environment flags and typed values.

Several boot-time readers (MK_DEBUG drives logging verbosity, CSP mode, CORS
permissiveness and the deployment-mode warnings) must agree on what counts as
"truthy". Centralising the rule here prevents the drift where one reader
accepted "on" and another silently did not. ``env_int`` applies the same
"parse once, fall back safely" contract to integer-valued variables.
"""
import logging
import os

logger = logging.getLogger("mediakeeper.env")

_TRUTHY_VALUES = frozenset({"true", "1", "yes", "on"})


def env_truthy(name: str) -> bool:
    """Return True when env var ``name`` holds a recognised truthy value.

    Recognised (case-insensitive, surrounding whitespace stripped): ``true``,
    ``1``, ``yes``, ``on``. Unset or anything else is False.
    """
    return os.getenv(name, "").strip().lower() in _TRUTHY_VALUES


def env_int(name: str, default: int) -> int:
    """Return env var ``name`` parsed as an int, or ``default``.

    Falls back to ``default`` (with a warning) when the value is unset,
    blank or not a valid integer, so a malformed operator-supplied value
    cannot crash the process at import time with an opaque traceback.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "Invalid integer for %s=%r; falling back to %d", name, raw, default
        )
        return default
