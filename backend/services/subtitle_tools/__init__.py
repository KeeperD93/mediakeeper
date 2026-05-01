"""
Outils de sous-titres : parsing SRT, detection desync, fix encodage, shift, compare.
Package split into modules (Rule 9, <= 300 lines).
"""
from ._parse import parse_srt_metadata
from .compare import compare_subtitles
from .desync import check_desync
from .encoding import fix_encoding
from .shift import shift_srt

__all__ = [
    "check_desync",
    "compare_subtitles",
    "fix_encoding",
    "parse_srt_metadata",
    "shift_srt",
]
