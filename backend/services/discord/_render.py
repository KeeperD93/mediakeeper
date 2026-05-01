"""Rendering helpers — variable substitution and embed construction."""
import re
import json
from datetime import datetime, timezone


def _hex_to_int(color_val) -> int:
    """Convert a hex color (#RRGGBB) or int to a Discord integer."""
    if isinstance(color_val, int):
        return color_val
    if isinstance(color_val, str) and color_val.startswith("#"):
        try:
            return int(color_val.lstrip("#"), 16)
        except ValueError:
            pass
    return 3066993  # default green


def _apply_vars(tmpl: str, vars_dict: dict) -> str:
    """Replace all <key> variables in the template."""
    for key, value in vars_dict.items():
        tmpl = tmpl.replace(f"<{key}>", str(value) if value else "")
    return tmpl


# Mapping FR → EN for variable names
# Allow users to write <title> or <titre> interchangeably
VAR_ALIASES = {
    "titre":          "title",
    "annee":          "year",
    "synopsis":       "overview",
    "genres":         "genres",
    "note":           "rating",
    "duree":          "runtime",
    "nb_saisons":     "seasons",
    "titre_serie":    "series_title",
    "num_saison":     "season_number",
    "saison":         "season",
    "nb_episodes":    "episodes",
    "titre_episode":  "episode_title",
    "episode":        "episode",
    "code":           "code",
    "tmdb":           "tmdb",
    "imgur":           "imgur",
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
    "date":           "date",
    "approuve_par":   "approved_by",
    "dispo":          "available",
    "total":          "total",
    "raison":         "reason",
    "type_probleme":  "issue_type",
    "description":    "description",
    "commentaire":    "comment",
    "resolu_par":     "resolved_by",
    "type_alerte":    "alert_type",
    "message":        "message",
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
    """
    fields = []
    match = re.search(r"<fields>(.*?)</fields>", tmpl, re.DOTALL)
    if match:
        try:
            fields = json.loads(match.group(1))
        except Exception:
            pass
        tmpl = tmpl[:match.start()] + tmpl[match.end():]
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
