"""Encoding detection and conversion to UTF-8."""
import logging
from pathlib import Path

import chardet

from services.path_config import validate_path_in_roots

from ._parse import _SUBTITLE_FILE_EXTENSIONS

logger = logging.getLogger("mediakeeper.subtitle_tools")


def fix_encoding(filepath: str, allow_any_path: bool = False) -> dict:
    """Detect the encoding of an SRT file and convert it to UTF-8 if needed.

    Return: original_encoding, converted, path.
    """
    try:
        if allow_any_path:
            target = Path(filepath).expanduser().resolve(strict=False)
        else:
            target, path_error = validate_path_in_roots(
                filepath,
                allow_missing=False,
                must_be_dir=False,
                allowed_suffixes=_SUBTITLE_FILE_EXTENSIONS,
                label="Subtitle file",
            )
            if path_error:
                return {
                    "original_encoding": "unknown",
                    "converted": False,
                    "path": filepath,
                    "error": path_error,
                }

        raw = target.read_bytes()
        detected = chardet.detect(raw)
        enc = detected.get("encoding") or "utf-8"

        if enc.upper() in ("UTF-8", "ASCII", "UTF-8-SIG"):
            return {"original_encoding": enc, "converted": False, "path": str(target)}

        text = raw.decode(enc, errors="replace")
        target.write_text(text, encoding="utf-8")
        logger.info(f"[subtitle_tools] Converted {target}: {enc} → UTF-8")

        return {"original_encoding": enc, "converted": True, "path": str(target)}

    except Exception:
        logger.exception("[subtitle_tools] Fix encoding failed for %r", filepath)
        return {"original_encoding": "unknown", "converted": False, "path": filepath, "error": "encoding_failed"}
