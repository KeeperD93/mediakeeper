"""ffprobe parser robustness against malformed numeric fields.

ffprobe emits non-numeric strings (e.g. "N/A") for size/duration/bitrate on
corrupted files; the parsers must degrade gracefully instead of raising and
turning the /metadata route into a 500.
"""
from api.media._metadata import _format_fps, _parse_format, _parse_streams


def test_format_fps_evaluates_fraction():
    """Fractional NTSC rates must be evaluated, not string-stripped."""
    assert _format_fps("24/1") == "24 fps"
    assert _format_fps("24000/1001") == "23.976 fps"
    assert _format_fps("30000/1001") == "29.97 fps"
    assert _format_fps("") == ""
    assert _format_fps("30/0") == ""


def test_parse_format_tolerates_non_numeric_values():
    result = _parse_format({"size": "N/A", "duration": "N/A", "bit_rate": "N/A"})
    assert result == {}


def test_parse_format_omits_absent_fields():
    assert _parse_format({}) == {}


def test_parse_format_parses_valid_values():
    result = _parse_format({"size": "1048576", "duration": "3661.0", "bit_rate": "128000"})
    assert result["size_bytes"] == 1048576  # raw machine code, formatted client-side
    assert result["duration_seconds"] == 3661.0
    assert result["overall_bitrate_bps"] == 128000


def test_parse_streams_tolerates_non_numeric_bitrate():
    streams = [
        {"codec_type": "video", "codec_name": "h264", "bit_rate": "N/A"},
        {"codec_type": "audio", "codec_name": "aac", "channels": 6, "bit_rate": "N/A"},
    ]
    video, audio, _ = _parse_streams(streams)
    assert len(video) == 1 and "bitrate_bps" not in video[0]
    assert len(audio) == 1 and "bitrate_bps" not in audio[0]


def test_parse_streams_parses_valid_bitrate():
    video, _, _ = _parse_streams(
        [{"codec_type": "video", "codec_name": "h264", "bit_rate": "5000000"}]
    )
    assert video[0]["bitrate_bps"] == 5000000


def test_parse_streams_emits_machine_codes():
    """Languages normalised to ISO codes, channels/flags as raw codes so the
    frontend can localize per viewer (no baked English strings)."""
    streams = [
        {
            "codec_type": "audio", "codec_name": "ac3", "channels": 6,
            "tags": {"language": "fre"},
            "disposition": {"default": 1},
        },
        {
            "codec_type": "subtitle", "codec_name": "subrip",
            "tags": {"language": "eng"},
            "disposition": {"forced": 1, "hearing_impaired": 1},
        },
    ]
    _, audio, subs = _parse_streams(streams)
    assert audio[0]["language_code"] == "fr"
    assert audio[0]["channels"] == 6
    assert audio[0]["is_default"] is True
    assert "bitrate_bps" not in audio[0]  # absent bit_rate stays omitted
    assert subs[0]["language_code"] == "en"
    assert subs[0]["is_forced"] is True
    assert subs[0]["is_hearing_impaired"] is True


def test_parse_streams_omits_falsy_disposition_and_channels():
    """Falsy values must be OMITTED, not emitted as False/0.

    The modal renders chips on key presence (``v-if='t.is_default'`` /
    channel counts), so a disposition flag set to 0 (or channels=0) must
    not appear as a key. Asserted on the track type that emits each flag:
    audio carries ``is_default``, subtitles carry ``is_forced`` /
    ``is_hearing_impaired``.
    """
    _, audio, subs = _parse_streams([
        {
            "codec_type": "audio", "codec_name": "aac", "channels": 0,
            "disposition": {"default": 0},
        },
        {
            "codec_type": "subtitle", "codec_name": "subrip",
            "tags": {"language": "eng"},
            "disposition": {"forced": 0, "hearing_impaired": 0},
        },
    ])
    assert "is_default" not in audio[0]  # audio emits is_default when truthy
    assert "channels" not in audio[0]    # channels=0 dropped by the falsy filter
    assert "is_forced" not in subs[0]            # subs emit is_forced when truthy
    assert "is_hearing_impaired" not in subs[0]
