"""Shared bounds and defaults for the per-user request quota.

Single source for the inclusive [1, 100] cap band (manual + auto) and the
nightly auto-recompute knob defaults, consumed by the settings registry, the
admin PATCH schema, the recompute engine and the bulk-edit sanitiser so the
four call sites can never drift.
"""

# Inclusive hard band for any per-user request cap (manual or auto).
QUOTA_BAND_MIN = 1
QUOTA_BAND_MAX = 100

# Default knobs for the nightly engagement-based auto recompute, keyed by the
# ``quota.auto.<key>`` suffix.
QUOTA_AUTO_DEFAULTS: dict[str, int] = {
    "min": 2,
    "max": 15,
    "window_days": 30,
    "grace_days": 14,
    "up_step": 1,
    "down_step": 1,
}
