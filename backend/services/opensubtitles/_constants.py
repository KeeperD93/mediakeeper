"""Constants sharedes du package opensubtitles."""
import logging

logger = logging.getLogger("mediakeeper.opensubtitles")

OS_API_BASE = "https://api.opensubtitles.com/api/v1"
OS_USER_AGENT = "Mediakeeper v1.0.0"
_SUBTITLE_FILE_EXTENSIONS = {".srt", ".sub", ".ssa", ".ass", ".vtt", ".idx"}
_IMAGE_CODECS = {
    "pgssub", "pgs", "vobsub", "dvdsub", "dvbsub",
    "hdmv_pgs_subtitle", "xsub", "dvd_subtitle", "hdmv_pgs",
}
