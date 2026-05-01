"""Side-by-side comparison of two OpenSubtitles subtitles."""
import tempfile
from pathlib import Path

from ._parse import parse_srt_metadata


async def compare_subtitles(
    db,
    file_id_a: int,
    file_id_b: int,
    media_duration_sec: float = 0,
) -> dict:
    """Download and compare two subtitle files.

    NOTE: consumes 2 downloads from the OpenSubtitles quota.
    """
    from services.opensubtitles import download_subtitle

    results: dict = {}
    dl_result: dict = {}

    for label, file_id in [("a", file_id_a), ("b", file_id_b)]:
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
            tmp_path = tmp.name

        dl_result = await download_subtitle(db, file_id, tmp_path, allow_any_path=True)
        if not dl_result.get("success"):
            return {"error": f"download_failed_{label}", "detail": dl_result.get("error", "")}

        content = Path(tmp_path).read_bytes()
        meta = parse_srt_metadata(content)

        results[label] = {**meta, "file_id": file_id}

        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

    diff = {
        "line_count_diff": abs(results["a"]["line_count"] - results["b"]["line_count"]),
        "duration_diff_sec": abs(results["a"]["duration_sec"] - results["b"]["duration_sec"]),
        "encoding_match": results["a"]["encoding"].upper() == results["b"]["encoding"].upper(),
        "size_diff": abs(results["a"]["size"] - results["b"]["size"]),
    }

    return {
        "a": results["a"],
        "b": results["b"],
        "diff": diff,
        "remaining_downloads": dl_result.get("remaining", 0),
    }
