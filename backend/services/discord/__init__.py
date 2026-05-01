"""
Service Discord — construction et envoi des payloads.

Structure d'un template de notification :
  - First line before \\n\\n = content Discord (texte au-dessus de l'embed)
  - Reste = description de l'embed
  - <fields> = bloc JSON inline for les embed fields : [{"name":"Titre","value":"Value","inline":true}]
  - image_style = "image" (large image at the bottom) or "thumbnail" (small on the right)
  - embed_color = couleur hex ou entier Discord

Package split into modules (Rule 9, <= 300 lines). Legacy imports
`from services.discord import X` continuent de functionner via les re-exports.
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
