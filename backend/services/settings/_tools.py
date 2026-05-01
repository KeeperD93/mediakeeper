"""Aggregate the tool config + detect the active media source."""
from sqlalchemy.ext.asyncio import AsyncSession

from ._kv import get_all_settings
from ._tools_def import TOOLS_DEFINITION


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
      "emby": { "enabled": True, "url": "...", "api_key": "..." },
      "plex": { "enabled": False, ... },
      ...
    }
    """
    all_settings = await get_all_settings(db)
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
                tool_config[f"{fk}_length"] = len(raw_value)
            else:
                tool_config[fk] = raw_value

        config[tool_key] = tool_config

    return config


async def get_active_media_source(db: AsyncSession) -> dict | None:
    """Return the active media source (emby/plex/jellyfin) or None."""
    config = await get_tools_config(db)
    for key in ("emby",):
        if config.get(key, {}).get("enabled"):
            return {"source": key, **config[key]}
    return None
