"""Guard-rail tests for ``backend/constants/env_vars.py``.

Defends against two silent-break classes a future contributor could
introduce:

- **Typo on a constant value** (e.g. ``TRUSTED_PROXES =
  "TRUSTED_PROXES"`` instead of ``TRUSTED_PROXIES =
  "TRUSTED_PROXIES"``). The lookup would silently fall back to the
  default value, runtime behaviour would shift, and no error would
  surface.

- **Drift between ``__all__`` and the actual definitions** (a new
  constant added but not listed in ``__all__``, or a stale entry left
  in ``__all__`` after a rename). The exported public API contract
  would diverge from what the module actually offers.

These tests stay cheap (run in milliseconds) and become more valuable
as the module grows beyond the initial 6 constants.
"""
from constants import env_vars


def test_each_constant_equals_its_own_name():
    """Every exported str constant must equal its own attribute name."""
    for name in env_vars.__all__:
        value = getattr(env_vars, name)
        assert isinstance(value, str), (
            f"{name} must be a str constant, got {type(value).__name__}"
        )
        assert value == name, (
            f"{name!r} = {value!r} — env var lookup would silently miss"
        )


def test_all_matches_public_str_constants():
    """``__all__`` must list exactly the public str module-level constants.

    Catches both directions: a new constant added without updating
    ``__all__``, or a stale entry left after a rename/removal.
    """
    actual_publics = {
        name
        for name, value in vars(env_vars).items()
        if not name.startswith("_") and isinstance(value, str)
    }
    declared = set(env_vars.__all__)

    missing = actual_publics - declared
    extra = declared - actual_publics

    assert not missing, f"missing from __all__: {sorted(missing)}"
    assert not extra, f"in __all__ but no module-level str found: {sorted(extra)}"
