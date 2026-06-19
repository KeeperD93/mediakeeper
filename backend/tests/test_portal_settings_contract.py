"""Contract: every Portal-settings key GET returns can be re-saved via PATCH.

GET /settings returns each setting under its de-prefixed name; PATCH accepts the
same name (field name or alias, via ``populate_by_name``). If a registry key is
ever added without a matching PortalSettingsUpdate alias, a Phase-2 draft re-save
(GET then PATCH the dirty keys) would 422 silently against ``extra="forbid"``.
These tests lock that registry<->schema contract.
"""
import pytest

from api.portal.admin import PortalSettingsUpdate, _without_portal_prefix
from services.portal.admin_settings import (
    PORTAL_SETTING_FLAGS,
    PORTAL_SETTING_FREETEXT,
    PORTAL_SETTING_HTML,
    PORTAL_SETTING_INTS,
    PORTAL_SETTING_STRINGS,
)
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

_SETTINGS = "/api/portal/admin/settings"


def _accepted_patch_keys() -> set[str]:
    # populate_by_name=True -> both the field name and its alias are accepted.
    keys: set[str] = set()
    for name, field in PortalSettingsUpdate.model_fields.items():
        keys.add(name)
        if field.alias:
            keys.add(field.alias)
    return keys


def test_every_registry_key_is_an_accepted_patch_key():
    registry = (
        list(PORTAL_SETTING_FLAGS)
        + list(PORTAL_SETTING_INTS)
        + list(PORTAL_SETTING_STRINGS)
        + list(PORTAL_SETTING_FREETEXT)
        + list(PORTAL_SETTING_HTML)
    )
    deprefixed = set(_without_portal_prefix(dict.fromkeys(registry)))
    missing = deprefixed - _accepted_patch_keys()
    assert not missing, f"GET keys with no PATCH alias (would 422 on re-save): {missing}"


@pytest.mark.asyncio
async def test_get_settings_round_trips_through_patch(client, db_session):
    user, _ = await make_portal_user(db_session, username="sc", display_name="SC", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    got = await client.get(_SETTINGS)
    assert got.status_code == 200, got.text

    # Re-saving exactly what GET returned must be accepted (no extra="forbid" 422).
    back = await client.patch(_SETTINGS, json=got.json())
    assert back.status_code == 200, back.text
