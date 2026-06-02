"""ffprobe parser robustness against malformed numeric fields.

ffprobe emits non-numeric strings (e.g. "N/A") for size/duration/bitrate on
corrupted files; the parsers must degrade gracefully instead of raising and
turning the /metadata route into a 500.
"""
from api.media._metadata import _parse_format, _parse_streams


def test_parse_format_tolerates_non_numeric_values():
    result = _parse_format({"size": "N/A", "duration": "N/A", "bit_rate": "N/A"})
    assert result == {}


def test_parse_format_omits_absent_fields():
    assert _parse_format({}) == {}


def test_parse_format_parses_valid_values():
    result = _parse_format({"size": "1048576", "duration": "3661.0", "bit_rate": "128000"})
    assert result["taille"]  # non-empty human-readable size
    assert result["duree"] == "1h 01m 01s"
    assert result["debit_global"] == "128 kbps"


def test_parse_streams_tolerates_non_numeric_bitrate():
    streams = [
        {"codec_type": "video", "codec_name": "h264", "bit_rate": "N/A"},
        {"codec_type": "audio", "codec_name": "aac", "channels": 6, "bit_rate": "N/A"},
    ]
    video, audio, _ = _parse_streams(streams)
    assert len(video) == 1 and "bitrate" not in video[0]
    assert len(audio) == 1 and "bitrate" not in audio[0]


def test_parse_streams_parses_valid_bitrate():
    video, _, _ = _parse_streams(
        [{"codec_type": "video", "codec_name": "h264", "bit_rate": "5000000"}]
    )
    assert video[0]["bitrate"] == "5000 kbps"
