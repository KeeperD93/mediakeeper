"""Defense-in-depth validators for uploaded archives.

The validators here are deliberately format-agnostic with respect to the
endpoint that consumes them: the backup restore endpoint and any future
consumer (RGPD export, third-party imports) call them with a context-
specific whitelist and decompressed-size cap.

All validators raise :class:`InvalidArchiveError` so callers can map a
single ``except`` clause to a stable, neutral HTTP 400 response.
"""

from __future__ import annotations

import zipfile
from typing import Iterable

# PKWARE APPNOTE.txt local-file-header signature for a regular ZIP archive.
_ZIP_MAGIC_LOCAL_HEADER = b"PK\x03\x04"
# End-of-central-directory record for an empty archive (no entries).
_ZIP_MAGIC_EMPTY_ARCHIVE = b"PK\x05\x06"
# PK\x07\x08 (spanned/multi-volume archives) is intentionally rejected:
# split ZIP archives require a multi-disk read which is meaningless for
# a single HTTP upload.

#: Number of bytes a caller must read to inspect the magic-byte signature.
ZIP_MAGIC_PREFIX_BYTES = 4

#: Per-entry decompression ratio above which an archive is treated as a
#: zip-bomb signal regardless of total size.
DEFAULT_MAX_RATIO_PER_ENTRY = 100


class InvalidArchiveError(Exception):
    """Raised when an uploaded archive fails an integrity check.

    ``code`` is a stable, neutral identifier suitable for the public HTTP
    detail field — never a path, hostname or operator hint.
    """

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_zip_magic_bytes(prefix: bytes) -> None:
    """Verify the first bytes match a recognised ZIP signature.

    ``prefix`` must contain at least :data:`ZIP_MAGIC_PREFIX_BYTES` bytes.
    Callers typically pass the leading slice of the upload buffer.
    """
    if len(prefix) < ZIP_MAGIC_PREFIX_BYTES:
        raise InvalidArchiveError("invalid_archive_format")
    head = prefix[:ZIP_MAGIC_PREFIX_BYTES]
    if head != _ZIP_MAGIC_LOCAL_HEADER and head != _ZIP_MAGIC_EMPTY_ARCHIVE:
        raise InvalidArchiveError("invalid_archive_format")


def validate_zip_not_empty(zf: zipfile.ZipFile) -> None:
    """Refuse archives that contain no file entries.

    Directory-only archives are also refused — the restore pipeline only
    consumes file payloads, so an empty payload set is always a programming
    or tampering error.
    """
    infolist = zf.infolist()
    if not infolist or all(info.is_dir() for info in infolist):
        raise InvalidArchiveError("archive_empty")


def validate_zip_namelist(
    zf: zipfile.ZipFile,
    *,
    allowed_names: Iterable[str] = (),
    allowed_prefixes: Iterable[str] = (),
) -> None:
    """Refuse archives whose namelist falls outside the caller's whitelist.

    Two complementary whitelists:
    * ``allowed_names`` — exact-match set (e.g. ``"manifest.json"``).
    * ``allowed_prefixes`` — directory-style prefixes that match any depth
      below them (e.g. ``"logs/"``).

    Path traversal is rejected outright: any entry whose normalised path
    contains a ``..`` component, starts with ``/``, or carries a Windows
    drive prefix raises :class:`InvalidArchiveError`.
    """
    allowed_name_set = set(allowed_names)
    allowed_prefix_tuple = tuple(allowed_prefixes)
    for name in zf.namelist():
        normalized = name.replace("\\", "/")
        # Reject absolute and traversal paths before any whitelist check.
        if normalized.startswith("/"):
            raise InvalidArchiveError("unsafe_archive_path")
        if len(normalized) >= 2 and normalized[1] == ":":
            raise InvalidArchiveError("unsafe_archive_path")
        if ".." in normalized.split("/"):
            raise InvalidArchiveError("unsafe_archive_path")
        if name in allowed_name_set:
            continue
        if any(name.startswith(prefix) for prefix in allowed_prefix_tuple):
            continue
        raise InvalidArchiveError("unknown_archive_entry")


def validate_zip_no_bomb(
    zf: zipfile.ZipFile,
    *,
    max_total_uncompressed: int,
    max_ratio_per_entry: int = DEFAULT_MAX_RATIO_PER_ENTRY,
) -> None:
    """Guard against zip-bomb archives via two metadata-only checks.

    * Total uncompressed size across all entries must not exceed
      ``max_total_uncompressed``.
    * Each entry's per-file ratio (uncompressed / compressed) must not
      exceed ``max_ratio_per_entry``.

    Both checks rely solely on :class:`zipfile.ZipInfo` metadata and never
    read entry contents — safe to run on a freshly opened archive before
    any decompression starts.
    """
    total = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        total += info.file_size
        if total > max_total_uncompressed:
            raise InvalidArchiveError("archive_too_large")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > max_ratio_per_entry:
                raise InvalidArchiveError(
                    "archive_compression_ratio_suspicious"
                )
