"""Single source of truth for parsing boolean-style environment flags.

Several boot-time readers (MK_DEBUG drives logging verbosity, CSP mode, CORS
permissiveness and the deployment-mode warnings) must agree on what counts as
"truthy". Centralising the rule here prevents the drift where one reader
accepted "on" and another silently did not.
"""
import os

_TRUTHY_VALUES = frozenset({"true", "1", "yes", "on"})


def env_truthy(name: str) -> bool:
    """Return True when env var ``name`` holds a recognised truthy value.

    Recognised (case-insensitive, surrounding whitespace stripped): ``true``,
    ``1``, ``yes``, ``on``. Unset or anything else is False.
    """
    return os.getenv(name, "").strip().lower() in _TRUTHY_VALUES
