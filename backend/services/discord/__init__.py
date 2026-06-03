"""
Discord service — building and sending notification payloads.

Notification template structure:
  - First line before \\n\\n = the Discord content (text shown above the embed)
  - Rest = the embed description
  - <fields> = inline JSON block for the embed fields: [{"name":"Title","value":"Value","inline":true}]
  - image_style = "image" (large image at the bottom) or "thumbnail" (small on the right)
  - embed_color = a Discord hex or integer colour

Package split into focused modules (kept under ~300 lines each). Legacy imports
`from services.discord import X` keep working through the re-exports.
"""
from ._defaults import DEFAULT_COLORS, DEFAULT_TEMPLATES, get_default_templates
from ._samples import SAMPLE_DATA, SAMPLE_SYSTEM
from ._vars import TPL_VARS, get_tpl_vars
from .payloads import build_discord_payload, build_system_payload
from .send import send_discord_test, send_discord_webhook

__all__ = [
    "DEFAULT_COLORS",
    "DEFAULT_TEMPLATES",
    "SAMPLE_DATA",
    "SAMPLE_SYSTEM",
    "TPL_VARS",
    "build_discord_payload",
    "build_system_payload",
    "get_default_templates",
    "get_tpl_vars",
    "send_discord_test",
    "send_discord_webhook",
]
