"""Pydantic schemas for the subtitle endpoints."""
from pydantic import BaseModel, ConfigDict


class SearchRequest(BaseModel):
    query: str = ""
    imdb_id: str = ""
    tmdb_id: str = ""
    season: int = 0
    episode: int = 0
    languages: str = ""
    file_path: str = ""      # pour hash automatique


class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_id: int
    destination: str              # chemin complet du fichier .srt a ecrire
    item_id: str = ""             # pour refresh Emby apres
    # Metadata for l'history (optionnels, envoyes par le frontend)
    media_name: str = ""
    media_type: str = ""
    series_name: str = ""
    season: int = 0
    episode: int = 0
    subtitle_id: str = ""
    file_name: str = ""
    language: str = ""
    quality_score: float = 0
    hash_match: bool = False
    hearing_impaired: bool = False
    foreign_parts_only: bool = False
    from_trusted: bool = False
    ai_translated: bool = False
    media_duration_sec: float = 0  # pour detection desync


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str


class RemoveStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    stream_index: int


class RemoveStreamsBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    stream_indices: list[int]


class ScanRequest(BaseModel):
    languages: list[str] | None = None
    library: str = ""


class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    languages: list[str] = ["fre", "eng"]
    include_hi: bool = False
    include_forced: bool = True
    exclude_ai: bool = True
    exclude_machine: bool = True
    prefer_trusted: bool = True
    prefer_hash_match: bool = True
    auto_download: bool = False
    min_score: float = 3.0


class AvailableCountRequest(BaseModel):
    items: list[dict]  # [{"imdb_id": "tt123", "tmdb_id": "456", "type": "Movie"}, ...]


class CompareRequest(BaseModel):
    file_id_a: int
    file_id_b: int
    media_duration_sec: float = 0


class FixEncodingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str


class ShiftSrtRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    offset_ms: int  # positif = retarder, negatif = avancer


class BatchDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[dict]
    profile_id: int = 0


class AuditRequest(BaseModel):
    languages: list[str] | None = None
    library: str = ""
    checks: list[str] = ["missing", "forced", "image_only"]


class BatchRemoveStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations: list[dict]  # [{"item_id": "xxx", "stream_index": 3}, ...]
