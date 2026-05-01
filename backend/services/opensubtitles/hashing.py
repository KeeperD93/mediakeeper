"""File hash (OpenSubtitles hash) + quality score."""
import os
import struct

from ._constants import logger


def compute_file_hash(filepath: str) -> str | None:
    """Calcule le hash OpenSubtitles d'un file (64-bit).
    Note: filepath must be the LOCAL path (already translated via _resolve_local_path)."""
    try:
        file_size = os.path.getsize(filepath)
        if file_size < 65536:
            return None

        hash_val = file_size
        block_size = 65536

        with open(filepath, "rb") as f:
            for _ in range(block_size // 8):
                buf = f.read(8)
                (val,) = struct.unpack("<q", buf)
                hash_val += val
                hash_val &= 0xFFFFFFFFFFFFFFFF

            f.seek(-block_size, 2)
            for _ in range(block_size // 8):
                buf = f.read(8)
                (val,) = struct.unpack("<q", buf)
                hash_val += val
                hash_val &= 0xFFFFFFFFFFFFFFFF

        return f"{hash_val:016x}"
    except Exception as e:
        logger.debug(f"[opensubtitles] Hash error for {filepath}: {e}")
        return None


def compute_quality_score(result: dict, has_hash_match: bool = False) -> float:
    """Compute a quality score of 1.0-5.0 for an OpenSubtitles result.

    Weights:
    - Base : 2.5
    - Hash match (file identique) : +1.0
    - Uploader de confiance : +0.6
    - Notes communautaires (0-10) : up to +0.5
    - Popularity (download_count): +0.1 to +0.2
    - Penalties: AI translated (-0.8), machine translated (-1.0)
    """
    score = 2.5

    if has_hash_match:
        score += 1.0

    if result.get("from_trusted"):
        score += 0.6

    ratings = result.get("ratings") or 0
    score += min(ratings / 20.0, 0.5)

    dl_count = result.get("download_count") or 0
    if dl_count > 10000:
        score += 0.2
    elif dl_count > 1000:
        score += 0.1

    if result.get("ai_translated"):
        score -= 0.8
    if result.get("machine_translated"):
        score -= 1.0

    return max(1.0, min(5.0, round(score, 1)))
