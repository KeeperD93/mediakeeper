"""Unit tests for the upload integrity validators."""
import io
import zipfile

import pytest

from core.file_validation import (
    DEFAULT_MAX_RATIO_PER_ENTRY,
    InvalidArchiveError,
    validate_zip_magic_bytes,
    validate_zip_namelist,
    validate_zip_no_bomb,
    validate_zip_not_empty,
)


def _make_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries:
            zf.writestr(name, payload)
    buf.seek(0)
    return buf


def _open_zip(buf):
    return zipfile.ZipFile(buf)


# --- validate_zip_magic_bytes -----------------------------------------------

def test_magic_bytes_accepts_regular_zip_signature():
    validate_zip_magic_bytes(b"PK\x03\x04rest")


def test_magic_bytes_accepts_empty_archive_signature():
    validate_zip_magic_bytes(b"PK\x05\x06rest")


def test_magic_bytes_rejects_spanned_archive_signature():
    with pytest.raises(InvalidArchiveError) as exc:
        validate_zip_magic_bytes(b"PK\x07\x08rest")
    assert exc.value.code == "invalid_archive_format"


def test_magic_bytes_rejects_unrelated_payload():
    with pytest.raises(InvalidArchiveError) as exc:
        validate_zip_magic_bytes(b"\x89PNG\r\n\x1a\n")
    assert exc.value.code == "invalid_archive_format"


def test_magic_bytes_rejects_truncated_prefix():
    with pytest.raises(InvalidArchiveError):
        validate_zip_magic_bytes(b"PK")


# --- validate_zip_not_empty -------------------------------------------------

def test_not_empty_accepts_archive_with_one_entry():
    buf = _make_zip([("a.json", b"{}")])
    with _open_zip(buf) as zf:
        validate_zip_not_empty(zf)


def test_not_empty_rejects_zero_entry_archive(tmp_path):
    path = tmp_path / "empty.zip"
    with zipfile.ZipFile(path, "w") as _:
        pass
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_not_empty(zf)
        assert exc.value.code == "archive_empty"


# --- validate_zip_namelist --------------------------------------------------

def test_namelist_accepts_whitelisted_exact_name():
    buf = _make_zip([("manifest.json", b"{}")])
    with _open_zip(buf) as zf:
        validate_zip_namelist(zf, allowed_names={"manifest.json"})


def test_namelist_accepts_whitelisted_prefix():
    buf = _make_zip([("logs/app.log", b"line"), ("logs/app.log.1", b"line")])
    with _open_zip(buf) as zf:
        validate_zip_namelist(zf, allowed_prefixes=("logs/",))


def test_namelist_rejects_unknown_entry():
    buf = _make_zip([("unexpected.bin", b"\x00")])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_namelist(zf, allowed_names={"manifest.json"})
        assert exc.value.code == "unknown_archive_entry"


def test_namelist_rejects_path_traversal_dotdot():
    buf = _make_zip([("../escape.txt", b"x")])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_namelist(zf, allowed_prefixes=("",))
        assert exc.value.code == "unsafe_archive_path"


def test_namelist_rejects_absolute_unix_path():
    buf = _make_zip([("/etc/passwd", b"x")])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_namelist(zf, allowed_prefixes=("",))
        assert exc.value.code == "unsafe_archive_path"


def test_namelist_rejects_windows_drive_path():
    buf = _make_zip([("C:/Windows/system32/config", b"x")])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_namelist(zf, allowed_prefixes=("",))
        assert exc.value.code == "unsafe_archive_path"


def test_namelist_rejects_backslash_traversal():
    buf = _make_zip([("foo\\..\\..\\evil", b"x")])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_namelist(zf, allowed_prefixes=("",))
        assert exc.value.code == "unsafe_archive_path"


# --- validate_zip_no_bomb ---------------------------------------------------

def test_no_bomb_accepts_realistic_archive():
    buf = _make_zip([("a.json", b"{}" * 10), ("b.json", b"{}" * 10)])
    with _open_zip(buf) as zf:
        validate_zip_no_bomb(zf, max_total_uncompressed=1024)


def test_no_bomb_rejects_total_uncompressed_over_cap():
    buf = _make_zip([("big.bin", b"A" * 2048)])
    with _open_zip(buf) as zf:
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_no_bomb(zf, max_total_uncompressed=512)
        assert exc.value.code == "archive_too_large"


def test_no_bomb_rejects_extreme_per_entry_ratio():
    # Highly compressible payload → ratio well above the 100x default.
    payload = b"A" * (200 * 1024)
    buf = _make_zip([("zeros.bin", payload)])
    with _open_zip(buf) as zf:
        info = zf.infolist()[0]
        assert info.compress_size > 0
        assert info.file_size / info.compress_size > DEFAULT_MAX_RATIO_PER_ENTRY
        with pytest.raises(InvalidArchiveError) as exc:
            validate_zip_no_bomb(
                zf,
                max_total_uncompressed=10 * 1024 * 1024,
            )
        assert exc.value.code == "archive_compression_ratio_suspicious"


def test_no_bomb_accepts_low_ratio_archive():
    # Random-ish payload → ratio close to 1, well under the cap.
    import os
    payload = os.urandom(4096)
    buf = _make_zip([("rand.bin", payload)])
    with _open_zip(buf) as zf:
        validate_zip_no_bomb(zf, max_total_uncompressed=10 * 1024 * 1024)


def test_no_bomb_ignores_directory_entries(tmp_path):
    path = tmp_path / "dir.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("a/", b"")  # directory entry
        zf.writestr("a/x.json", b"{}")
    with zipfile.ZipFile(path) as zf:
        validate_zip_no_bomb(zf, max_total_uncompressed=1024)
