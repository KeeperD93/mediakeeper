"""Rendering helpers — variable substitution and embed construction."""
import json
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("mediakeeper.notifications.discord")


def _hex_to_int(color_val: int | str | None) -> int:
    """Convert a hex color (#RRGGBB) or int to a Discord integer."""
    # bool is a subclass of int — exclude it so a stray ``color: true`` in
    # an admin config falls back to the default instead of rendering as 1.
    if isinstance(color_val, int) and not isinstance(color_val, bool):
        return color_val
    if isinstance(color_val, str) and color_val.startswith("#"):
        try:
            return int(color_val.lstrip("#"), 16)
        except ValueError:
            pass
    return 3066993  # default green


# Variables whose values are already valid Discord markdown — the engine
# composes them itself (e.g. ``[Fiche TMDB](url)``) and they must NOT be
# double-escaped.
PREFORMATTED_VARS = frozenset({
    "tmdb", "tmdb_url", "imgur",
    # Pre-built markdown links — the underlying raw name is escaped
    # at construction site in ``payloads.py`` before being wrapped in
    # ``[name](url)``, so re-escaping here would mangle the link.
    "titre", "title", "titre_serie", "series_title",
})

# Discord markdown control characters. Escaping them defangs poisoned
# media titles such as ``[click](https://evil)`` arriving from TMDB,
# while leaving the template's own formatting (``**bold**``, ``[link
# label](url)``) intact because templates are admin-edited, not
# user-supplied.
_DISCORD_MD_RE = re.compile(r"([\\*_~|`>\[\]()])")


def escape_discord_markdown(value: str) -> str:
    """Backslash-escape Discord markdown control characters in ``value``.

    Discord's parser interprets ``*_~|`` and link brackets even when
    they appear deep inside an otherwise-plain text field. We escape
    them so a hostile content source (TMDB title with ``[click](evil)``,
    chat-relayed username with ``**ping**`` etc.) cannot smuggle
    formatting / clickable links into the rendered embed.
    """
    return _DISCORD_MD_RE.sub(r"\\\1", value)


def _apply_vars(tmpl: str, vars_dict: dict) -> str:
    """Replace all ``<key>`` variables in the template.

    Values are markdown-escaped before substitution unless the key is
    in :data:`PREFORMATTED_VARS` (URLs, engine-composed link blocks)
    where escaping would break the intended formatting.
    """
    for key, value in vars_dict.items():
        if value:
            text = str(value)
            if key not in PREFORMATTED_VARS:
                text = escape_discord_markdown(text)
        else:
            text = ""
        tmpl = tmpl.replace(f"<{key}>", text)
    return tmpl


# Mapping FR → EN for variable names
# Allow users to write <title> or <titre> interchangeably
# Self-referential entries (key == value, e.g. "genres": "genres") are
# omitted on purpose: _add_aliases skips them anyway since the key is already
# present, so they were dead weight.
VAR_ALIASES = {
    "titre":          "title",
    "annee":          "year",
    "synopsis":       "overview",
    "note":           "rating",
    "duree":          "runtime",
    "nb_saisons":     "seasons",
    "titre_serie":    "series_title",
    "num_saison":     "season_number",
    "saison":         "season",
    "nb_episodes":    "episodes",
    "titre_episode":  "episode_title",
    "nom_serveur":    "server_name",
    "heure":          "time",
    "titre_media":    "media_title",
    "bibliotheque":   "library",
    "fichier_1":      "file_1",
    "fichier_2":      "file_2",
    "taille_1":       "size_1",
    "taille_2":       "size_2",
    "utilisateur":    "user",
    "titre_demande":  "request_title",
    "type_media":     "media_type",
    "approuve_par":   "approved_by",
    "dispo":          "available",
    "raison":         "reason",
    "type_probleme":  "issue_type",
    "commentaire":    "comment",
    "resolu_par":     "resolved_by",
    "type_alerte":    "alert_type",
    "severite":       "severity",
}
# Reverse mapping EN → FR
VAR_ALIASES_REV = {v: k for k, v in VAR_ALIASES.items()}


def _add_aliases(vars_dict: dict) -> dict:
    """Add EN↔FR aliases so that <title> and <titre> both work."""
    enriched = dict(vars_dict)
    for key, value in list(vars_dict.items()):
        if key in VAR_ALIASES and VAR_ALIASES[key] not in enriched:
            enriched[VAR_ALIASES[key]] = value
        if key in VAR_ALIASES_REV and VAR_ALIASES_REV[key] not in enriched:
            enriched[VAR_ALIASES_REV[key]] = value
    return enriched


def _parse_fields(tmpl: str) -> tuple[str, list]:
    """
    Extract embed fields from the template.
    Syntax: <fields>[{"name":"N","value":"V","inline":true}]</fields>

    Linear-time rewrite of the previous ``re.search(r"<fields>(.*?)</fields>",
    ..., re.DOTALL)``, which CodeQL flagged as polynomial-degree
    (py/polynomial-redos #145). ``str.find`` is O(n) garanti and the
    code reads more naturally than a regex anyway. Only the first
    ``<fields>...</fields>`` block is processed (matches previous
    behaviour: ``re.search`` returns the first non-overlapping match).
    """
    fields = []
    start_marker = "<fields>"
    end_marker = "</fields>"
    start = tmpl.find(start_marker)
    if start != -1:
        body_start = start + len(start_marker)
        end = tmpl.find(end_marker, body_start)
        if end != -1:
            try:
                fields = json.loads(tmpl[body_start:end])
            except Exception as exc:
                # Best-effort: a malformed <fields> block degrades to an
                # empty fields list rather than failing the whole embed.
                # Emit at DEBUG so an admin tuning a template can grep the
                # cause without polluting INFO logs.
                logger.debug(
                    "[discord] _parse_fields JSON invalid: %s", type(exc).__name__,
                )
            tmpl = tmpl[:start] + tmpl[end + len(end_marker):]
    return tmpl.strip(), fields


def _build_embed(
    tmpl: str,
    color: int,
    image_url: str,
    image_style: str,  # "image" | "thumbnail"
) -> tuple[str, dict]:
    """
    Build the Discord embed payload from the final template.
    Return (content_text, embed_dict).
    """
    tmpl, fields = _parse_fields(tmpl)

    if "\n\n" in tmpl:
        parts = tmpl.split("\n\n", 1)
        content_text = parts[0].strip()
        embed_desc = parts[1].strip()
    else:
        content_text = ""
        embed_desc = tmpl.strip()

    content_text = content_text.replace("<imgur>", "").strip()
    embed_desc   = embed_desc.replace("<imgur>", "").strip()

    if content_text:
        content_text = "\u200B\n" + content_text

    embed = {
        "description": embed_desc,
        "color":       color,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "footer":      {"text": "MediaKeeper"},
    }

    if fields:
        embed["fields"] = fields

    if image_url:
        if image_style == "thumbnail":
            embed["thumbnail"] = {"url": image_url}
        else:
            embed["image"] = {"url": image_url}

    return content_text, embed
