"""Aggregate the tool config + detect the active media source."""
from sqlalchemy.ext.asyncio import AsyncSession

from constants.tools import TOOL_EMBY
from ._emby_urls import get_emby_server_id
from ._kv import get_all_settings
from ._tools_def import TOOLS_DEFINITION

# Width of the asterisk mask returned for a configured secret. A fixed value
# rather than len(secret) so the admin UI never leaks the real secret length.
MASKED_SECRET_LENGTH = 12


def _is_secret_field(field: dict) -> bool:
    return field.get("type") == "password" or field.get("key") in {"api_key", "password"}


async def get_tools_config(
    db: AsyncSession,
    *,
    mask_secrets: bool = False,
) -> dict:
    """
    Return the full config of every tool:
    {
      "emby": { "enabled": True, "url": "...", "api_key": "...", "server_id": "..." },
      "plex": { "enabled": False, ... },
      ...
    }
    """
    # Tool config needs plaintext: it surfaces editable secret values to the
    # admin UI and uses url/api_key to query Emby. get_all_settings is
    # fail-safe (encrypted) by default, so plaintext is opted into explicitly.
    all_settings = await get_all_settings(db, decrypt_sensitive=True)
    config = {}

    for tool_key, tool_def in TOOLS_DEFINITION.items():
        tool_config = {
            "enabled": all_settings.get(f"{tool_key}.enabled", "false") == "true",
            "label":   tool_def["label"],
            "type":    tool_def["type"],
            "icon":    tool_def["icon"],
        }
        for field in tool_def["fields"]:
            fk = field["key"]
            raw_value = all_settings.get(f"{tool_key}.{fk}", "")
            if mask_secrets and _is_secret_field(field):
                tool_config[fk] = ""
                tool_config[f"{fk}_configured"] = bool(raw_value)
                tool_config[f"{fk}_length"] = MASKED_SECRET_LENGTH if raw_value else 0
            else:
                tool_config[fk] = raw_value

        # Emby deep-links opened in the user's browser need the
        # ``serverId`` query param — without it Emby Web 4.9+ loads
        # the SPA shell but resolves the route to a blank page.
        # Surface the cached server_id here so the admin dashboard
        # (which builds its hero "Watch on Emby" link client-side)
        # can append it the same way ``build_emby_deep_link`` does
        # on the portal. Uses the raw url/api_key in this scope so
        # the /System/Info call still works when ``mask_secrets`` is
        # True for the caller.
        if tool_key == TOOL_EMBY and tool_config["enabled"]:
            tool_config["server_id"] = await get_emby_server_id({
                "url":     all_settings.get(f"{tool_key}.url", ""),
                "api_key": all_settings.get(f"{tool_key}.api_key", ""),
            })

        config[tool_key] = tool_config

    return config


async def get_active_media_source(db: AsyncSession) -> dict | None:
    """Return the active media source (emby/plex/jellyfin) or None."""
    config = await get_tools_config(db)
    for key in (TOOL_EMBY,):
        if config.get(key, {}).get("enabled"):
            return {"source": key, **config[key]}
    return None
