"""
Interface abstraite for les sources de sous-titres.
Permet d'ajouter de new fournisseurs (Addic7ed, Subscene, etc.)
en implementant la classe SubtitleSource.
"""
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession


class SubtitleSource(ABC):
    """Interface for les fournisseurs de sous-titres."""

    @abstractmethod
    async def search(
        self,
        db: AsyncSession,
        query: str = "",
        imdb_id: str = "",
        tmdb_id: str = "",
        season: int = 0,
        episode: int = 0,
        languages: str = "",
        moviehash: str = "",
    ) -> dict:
        """Recherche de sous-titres. Return {"results": [...], "total": int}."""

    @abstractmethod
    async def download(
        self,
        db: AsyncSession,
        file_id: int,
        destination_path: str,
    ) -> dict:
        """Telecharge un sous-titre. Return {"success": bool, "path": str, ...}."""

    @abstractmethod
    async def get_quota(self, db: AsyncSession) -> dict:
        """Return les infos de quota."""

    @abstractmethod
    def source_name(self) -> str:
        """Return l'identifiant de la source."""
