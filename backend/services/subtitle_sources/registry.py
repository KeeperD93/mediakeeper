"""
Registre des sources de sous-titres.
Permet d'ajouter et de recuperer des sources dynamicment.
"""
from services.subtitle_sources import SubtitleSource

_sources: dict[str, SubtitleSource] = {}


def register_source(source: SubtitleSource) -> None:
    """Record une source de sous-titres."""
    _sources[source.source_name()] = source


def get_source(name: str) -> SubtitleSource | None:
    """Recupere une source par son nom."""
    return _sources.get(name)


def get_all_sources() -> list[SubtitleSource]:
    """Return all les sources enregistrees."""
    return list(_sources.values())


def get_source_names() -> list[str]:
    """Return les noms de all les sources enregistrees."""
    return list(_sources.keys())
