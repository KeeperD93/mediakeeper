"""Build Discord payloads (media + system)."""

from services.tmdb import get_media_detail, tmdb_language, LANGUAGE
from services.tmdb_episode import get_episode_detail, get_season_detail

from ._defaults import DEFAULT_COLORS, get_default_templates
from ._render import (
    _hex_to_int, _apply_vars, _add_aliases, _build_embed,
    escape_discord_markdown,
)
from ._images import _get_image_url

# Link label injected into the ``<tmdb>`` template variable, per webhook language.
_TMDB_LINK_LABEL = {"fr": "Fiche TMDB", "en": "TMDB page"}


async def _resolve_system_lang(db) -> str:
    """Fetch the instance default portal language for system messages; fallback FR."""
    if db is None:
        return "fr"
    try:
        from services.settings import get_portal_default_language
        return await get_portal_default_language(db, default="fr")
    except Exception:
        return "fr"


async def _localized_media_text(
    item: dict, item_type: str, tmdb_id, tmdb_type: str, lang: str, db,
) -> dict:
    """Re-resolve an item's title + synopsis to ``lang`` via TMDB, per type.

    Emby serves Name/Overview in the library language; this swaps in the
    localized values — series/film title, plus season/episode-level synopsis
    when the item is a season/episode. Every field falls back to the Emby
    value, so a missing tmdb_id or a TMDB failure degrades gracefully.
    """
    out = {
        "name": item.get("Name", ""),
        "series": item.get("SeriesName", ""),
        "overview": item.get("Overview", ""),
    }
    # Default language: Emby already serves the text, so keep it and skip the
    # TMDB round-trip — same short-circuit as localize_emby_items.
    if not tmdb_id or tmdb_language(lang) == LANGUAGE:
        return out
    try:
        tid = int(tmdb_id)
    except (TypeError, ValueError):
        return out
    detail = await get_media_detail(tmdb_type, tid, db, locale=lang)
    if detail and not detail.get("error"):
        title = (detail.get("title") or "").strip()
        if title:
            out["series"] = title
            if item_type in ("Movie", "Series"):
                out["name"] = title
        if item_type in ("Movie", "Series", "Grouped"):
            out["overview"] = (detail.get("overview") or "").strip() or out["overview"]
    if item_type == "Season":
        s_num = item.get("IndexNumber", 0)
        if s_num:
            sd = await get_season_detail(tid, s_num, db, locale=lang)
            out["overview"] = sd.get("overview") or out["overview"]
    elif item_type == "Episode":
        s_num = item.get("ParentIndexNumber", 0)
        e_num = item.get("IndexNumber", 0)
        if s_num and e_num:
            ed = await get_episode_detail(tid, s_num, e_num, db, locale=lang)
            out["name"] = ed.get("name") or out["name"]
            out["overview"] = ed.get("overview") or out["overview"]
    return out


async def build_discord_payload(
    item: dict,
    wh_config: dict,
    emby_url: str,
    emby_api_key: str,
    imgur_client_id: str = "",
    imgur_client_secret: str = "",
    db=None,
) -> dict:
    """
    Build the full Discord payload for a media addition.
    wh_config = the full webhook (contains templates, settings, lang...)
    """
    templates   = wh_config.get("templates", {}) or {}
    settings    = wh_config.get("settings",  {}) or {}
    lang        = wh_config.get("lang") or await _resolve_system_lang(db)
    label_tmdb  = _TMDB_LINK_LABEL.get(lang, _TMDB_LINK_LABEL["en"])

    item_type = item.get("Type", "")

    # ── Template selection ──
    if item_type == "Grouped":
        tpl_key = "added_grouped"
    elif item_type == "Episode":
        tpl_key = "added_episode"
    elif item_type == "Season":
        tpl_key = "added_season"
    elif item_type == "Series":
        tpl_key = "added_series"
    else:
        tpl_key = "added_movie"

    raw_tpl = templates.get(tpl_key) or get_default_templates(lang).get(tpl_key, "")
    tpl_settings = settings.get(tpl_key, {})

    color       = _hex_to_int(tpl_settings.get("color", DEFAULT_COLORS.get(tpl_key, 5763719)))
    image_style = tpl_settings.get("image_style", "image")  # "image" | "thumbnail"

    # ── Contextual data ──
    year    = str(item.get("ProductionYear") or item.get("PremiereDate", "")[:4] or "")

    provider_ids = item.get("ProviderIds", {})
    tmdb_id = provider_ids.get("Tmdb")
    if not tmdb_id and item_type == "Episode":
        tmdb_id = item.get("SeriesProviderIds", {}).get("Tmdb")

    tmdb_type = "tv" if item_type in ("Episode", "Season", "Series", "Grouped") else "movie"
    tmdb_base  = f"https://www.themoviedb.org/{tmdb_type}/{tmdb_id}" if tmdb_id else ""

    # Re-resolve title + synopsis to the webhook language (Emby serves them in
    # the library language); each field falls back to the Emby value.
    loc = await _localized_media_text(item, item_type, tmdb_id, tmdb_type, lang, db)
    name = loc["name"]
    overview = loc["overview"]
    if overview:
        lines = overview.splitlines()
        short = "\n".join(lines[:6])
        if len(short) > 350:
            short = short[:350].rsplit(" ", 1)[0]
        if short != overview:
            overview = short + "..."

    genres = ", ".join(item.get("Genres", [])[:3]) if item.get("Genres") else ""
    note   = item.get("CommunityRating", "")
    note   = f"{note:.1f}" if isinstance(note, float) else str(note) if note else ""
    duree  = str(item.get("RunTimeTicks", 0) // 600_000_000) if item.get("RunTimeTicks") else ""

    if item_type == "Episode":
        image_id = item.get("SeriesId", "")
    elif item_type == "Season":
        image_id = item.get("SeriesId", item.get("Id", ""))
    else:
        image_id = item.get("Id", "")

    # ── Variables based on the type ──
    if item_type == "Episode":
        series  = loc["series"]
        s_num   = item.get("ParentIndexNumber", 0)
        e_num   = item.get("IndexNumber", 0)
        code    = f"S{s_num:02d}E{e_num:02d}" if s_num and e_num else ""
        tmdb_ep = f"{tmdb_base}/season/{s_num}/episode/{e_num}" if tmdb_base and s_num and e_num else tmdb_base
        tmdb_lnk = f"[{label_tmdb}]({tmdb_ep})" if tmdb_ep else ""
        # Escape the raw series name BEFORE wrapping it in markdown link
        # syntax. The wrapped value is registered as preformatted in
        # ``_render.PREFORMATTED_VARS`` so ``_apply_vars`` keeps it
        # clickable; without the early escape, a hostile series name
        # like ``[click](evil)`` would smuggle a malicious link.
        safe_series = escape_discord_markdown(series)
        title_linked = f"[{safe_series}]({tmdb_base})" if tmdb_base else safe_series
        vars_dict = {
            "titre_serie":   title_linked,
            "titre_episode": name,
            "saison":        f"Saison {s_num}" if s_num else "",
            "episode":       f"Épisode {e_num}" if e_num else "",
            "code":          code,
            "annee":         year,
            "synopsis":      overview,
            "tmdb":          tmdb_lnk,
        }

    elif item_type == "Grouped":
        series   = loc["series"]
        s_num    = item.get("IndexNumber", 0)
        nb_ep    = item.get("ChildCount", "")
        tmdb_s   = f"{tmdb_base}/season/{s_num}" if tmdb_base and s_num else tmdb_base
        tmdb_lnk = f"[{label_tmdb}]({tmdb_s})" if tmdb_s else ""
        safe_series = escape_discord_markdown(series)
        title_linked = f"[{safe_series}]({tmdb_base})" if tmdb_base else safe_series
        image_id = item.get("SeriesId", item.get("Id", ""))
        # Admins frequently customise the grouped template to mirror
        # ``added_season`` (with ``<synopsis>`` included). The synthetic
        # Grouped item carries an English placeholder Overview by default,
        # but post-promotion enrichment may have replaced it with the
        # series-level synopsis — surface whatever we have.
        vars_dict = {
            "titre_serie": title_linked,
            "saison":      f"Saison {s_num}" if s_num else "",
            "nb_episodes": str(nb_ep) if nb_ep else "",
            "annee":       year,
            "synopsis":    overview,
            "tmdb":        tmdb_lnk,
            # EN aliases
            "series_title": title_linked,
            "season":       f"Season {s_num}" if s_num else "",
            "episodes":     str(nb_ep) if nb_ep else "",
            "overview":     overview,
        }

    elif item_type == "Season":
        series   = loc["series"]
        s_num    = item.get("IndexNumber", 0)
        nb_ep    = item.get("ChildCount", "")
        tmdb_s   = f"{tmdb_base}/season/{s_num}" if tmdb_base and s_num else tmdb_base
        tmdb_lnk = f"[{label_tmdb}]({tmdb_s})" if tmdb_s else ""
        safe_series = escape_discord_markdown(series)
        title_linked = f"[{safe_series}]({tmdb_base})" if tmdb_base else safe_series
        vars_dict = {
            "titre_serie": title_linked,
            "num_saison":  str(s_num) if s_num else "",
            "saison":      f"Saison {s_num}" if s_num else "",
            "nb_episodes": str(nb_ep) if nb_ep else "",
            "annee":       year,
            "synopsis":    overview,
            "tmdb":        tmdb_lnk,
        }

    elif item_type == "Series":
        nb_s     = item.get("ChildCount", "")
        tmdb_lnk = f"[{label_tmdb}]({tmdb_base})" if tmdb_base else ""
        safe_name = escape_discord_markdown(name)
        title_linked = f"[{safe_name}]({tmdb_base})" if tmdb_base else safe_name
        vars_dict = {
            "titre":      title_linked,
            "annee":      year,
            "synopsis":   overview,
            "genres":     genres,
            "note":       note,
            "nb_saisons": str(nb_s) if nb_s else "",
            "tmdb":       tmdb_lnk,
        }

    else:  # Movie
        tmdb_lnk = f"[{label_tmdb}]({tmdb_base})" if tmdb_base else ""
        safe_name = escape_discord_markdown(name)
        title_linked = f"[{safe_name}]({tmdb_base})" if tmdb_base else safe_name
        vars_dict = {
            "titre":   title_linked,
            "annee":   year,
            "synopsis":overview,
            "genres":  genres,
            "note":    note,
            "duree":   duree,
            "tmdb":    tmdb_lnk,
        }

    tmpl = _apply_vars(raw_tpl, _add_aliases(vars_dict))

    image_url = ""
    if "<imgur>" in tmpl:
        image_url = await _get_image_url(
            image_id,
            emby_url,
            emby_api_key,
            imgur_client_id,
            tmdb_id=tmdb_id or "",
            tmdb_type=tmdb_type,
            db=db,
        )

    content_text, embed = _build_embed(tmpl, color, image_url, image_style)

    return {
        "username": "MediaKeeper",
        "content":  content_text,
        "embeds":   [embed],
    }


async def build_system_payload(
    tpl_key: str,
    vars_dict: dict,
    wh_config: dict,
    db=None,
) -> dict:
    """Build the payload for system notifications (non-media)."""
    templates = wh_config.get("templates", {}) or {}
    settings  = wh_config.get("settings",  {}) or {}
    lang      = wh_config.get("lang") or await _resolve_system_lang(db)

    raw_tpl = templates.get(tpl_key) or get_default_templates(lang).get(tpl_key, "📢 **<title>**\n\n<description>")
    tpl_settings = settings.get(tpl_key, {})

    color       = _hex_to_int(tpl_settings.get("color", DEFAULT_COLORS.get(tpl_key, 3066993)))
    image_style = tpl_settings.get("image_style", "thumbnail")

    tmpl = _apply_vars(raw_tpl, _add_aliases(vars_dict))
    content_text, embed = _build_embed(tmpl, color, "", image_style)

    return {
        "username": "MediaKeeper",
        "content":  content_text,
        "embeds":   [embed],
    }
