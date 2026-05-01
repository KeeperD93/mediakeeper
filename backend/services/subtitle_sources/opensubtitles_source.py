"""
Adapter OpenSubtitles for l'interface SubtitleSource.
Delegue au service existant opensubtitles.py.
"""
from services.subtitle_sources import SubtitleSource


class OpenSubtitlesSource(SubtitleSource):
    """Adapter wrapping le service opensubtitles.py existant."""

    async def search(self, db, query="", imdb_id="", tmdb_id="",
                     season=0, episode=0, languages="", moviehash="") -> dict:
        from services.opensubtitles import search_subtitles
        return await search_subtitles(
            db, query=query, imdb_id=imdb_id, tmdb_id=tmdb_id,
            season=season, episode=episode, languages=languages, moviehash=moviehash,
        )

    async def download(self, db, file_id, destination_path) -> dict:
        from services.opensubtitles import download_subtitle
        return await download_subtitle(db, file_id, destination_path)

    async def get_quota(self, db) -> dict:
        from services.opensubtitles import get_quota
        return await get_quota(db)

    def source_name(self) -> str:
        return "opensubtitles"
