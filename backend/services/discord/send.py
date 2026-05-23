"""Sending Discord webhooks (tests + production)."""
import logging

from core.http_client import get_external_client
from core.url_safety import is_discord_webhook_url
from core.webhooks import post_signed_with_retry, webhook_log_id

from ._defaults import DEFAULT_COLORS, get_default_templates
from ._render import _hex_to_int, _apply_vars, _add_aliases, _build_embed
from ._samples import SAMPLE_DATA, SAMPLE_SYSTEM

logger = logging.getLogger("mediakeeper.notifications.discord")


async def send_discord_test(
    webhook_url: str,
    wh_config: dict = None,
    test_type: str = "movie",
) -> dict:
    """Send a test message with sample data."""
    # Strict hostname check defeats ``https://discord.com@evil.com/...``
    # userinfo bypasses and trailing-dot subdomain tricks.
    if not is_discord_webhook_url(webhook_url):
        return {"error": "Invalid Discord webhook URL."}

    wh_config = wh_config or {}
    templates = wh_config.get("templates", {}) or {}
    settings  = wh_config.get("settings",  {}) or {}

    # Map test_type → tpl_key + data
    type_map = {
        "movie":   ("added_movie",   SAMPLE_DATA["movie"]),
        "series":  ("added_series",  SAMPLE_DATA["series"]),
        "season":  ("added_season",  SAMPLE_DATA["season"]),
        "episode": ("added_episode", SAMPLE_DATA["episode"]),
    }
    for syskey, sysdata in SAMPLE_SYSTEM.items():
        type_map[syskey] = (syskey, sysdata)

    if test_type not in type_map:
        return {"error": f"Unknown test type: {test_type}"}

    tpl_key, vars_src = type_map[test_type]
    vars_dict = dict(vars_src)  # copy so we don't mutate SAMPLE_DATA
    lang = wh_config.get("lang", "fr")
    raw_tpl = templates.get(tpl_key) or get_default_templates(lang).get(tpl_key, "")
    tpl_settings = settings.get(tpl_key, {})
    color       = _hex_to_int(tpl_settings.get("color", DEFAULT_COLORS.get(tpl_key, 5763719)))
    image_style = tpl_settings.get("image_style", "image")

    image_url = vars_dict.pop("imgur", "")
    tmpl = _apply_vars(raw_tpl, _add_aliases(vars_dict))
    if "<imgur>" in tmpl and image_url:
        tmpl = tmpl.replace("<imgur>", "")  # put the image in the embed
    else:
        image_url = ""

    content_text, embed = _build_embed(tmpl, color, image_url, image_style)
    payload = {"username": "MediaKeeper", "content": content_text, "embeds": [embed]}
    log_id = webhook_log_id(webhook_url)

    try:
        client = get_external_client()
        res = await post_signed_with_retry(
            client, webhook_url, payload, timeout=10.0
        )
        if res.status_code in (200, 204):
            return {"success": True}
        logger.warning(
            "[discord] test webhook %s rejected delivery (status=%s)",
            log_id, res.status_code,
        )
        return {"error": f"Discord rejected (HTTP {res.status_code})"}
    except Exception as e:
        # ``e`` formatting is restricted to the exception class so a
        # malformed httpx error never leaks the webhook URL into logs.
        logger.warning(
            "[discord] test webhook %s delivery exception (%s)",
            log_id, type(e).__name__,
        )
        return {"error": "Unable to reach Discord."}


async def send_discord_webhook(webhook_url: str, payload: dict) -> bool:
    if not is_discord_webhook_url(webhook_url):
        return False
    log_id = webhook_log_id(webhook_url)
    try:
        client = get_external_client()
        res = await post_signed_with_retry(
            client, webhook_url, payload, timeout=10.0
        )
        if res.status_code in (200, 204):
            return True
        logger.warning(
            "[discord] webhook %s rejected delivery (status=%s)",
            log_id, res.status_code,
        )
        return False
    except Exception as e:
        logger.warning(
            "[discord] webhook %s delivery exception (%s)",
            log_id, type(e).__name__,
        )
        return False
