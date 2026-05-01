"""Emby item analysis: detection of individual issues."""
from sqlalchemy import case

from models.healthcheck import HealthCheckResult

from .config import OBSOLETE_CONTAINERS, OBSOLETE_VIDEO_CODECS


def _analyze_item(item: dict, config: dict) -> list[dict]:
    """Analyze an Emby item and return the list of detected issues."""
    issues = []
    sources = item.get("MediaSources") or []
    if not sources:
        return issues

    source = sources[0]
    container = (source.get("Container") or "").lower()
    file_size = source.get("Size") or 0
    bitrate = source.get("Bitrate") or 0

    streams = item.get("MediaStreams") or source.get("MediaStreams") or []
    video_streams = [s for s in streams if s.get("Type") == "Video"]
    audio_streams = [s for s in streams if s.get("Type") == "Audio"]

    # 1. Obsolete container
    if config.get("obsolete_containers_enabled", True) and container in OBSOLETE_CONTAINERS:
        issues.append({
            "type": "obsolete_container",
            "severity": "warning",
            "detail": container.upper(),
        })

    # 2. Obsolete video codec
    if config.get("obsolete_codecs_enabled", True):
        for vs in video_streams:
            codec = (vs.get("Codec") or "").lower()
            if codec in OBSOLETE_VIDEO_CODECS:
                issues.append({
                    "type": "obsolete_codec",
                    "severity": "warning",
                    "detail": codec.upper(),
                })

    # 3. Resolution basse
    if config.get("low_resolution_enabled", True):
        min_height = config.get("min_resolution_height", 720)
        for vs in video_streams:
            height = vs.get("Height") or 0
            if 0 < height < min_height:
                issues.append({
                    "type": "low_resolution",
                    "severity": "info",
                    "detail": f"{height}p",
                })

    # 4. Bitrate anormalment bas
    if config.get("low_bitrate_enabled", True):
        min_bitrate = config.get("min_video_bitrate_kbps", 1000)
        bitrate_kbps = bitrate // 1000 if bitrate else 0
        if video_streams and 0 < bitrate_kbps < min_bitrate:
            issues.append({
                "type": "low_bitrate",
                "severity": "warning",
                "detail": f"{bitrate_kbps} kbps",
            })

    # 5. No piste audio
    if config.get("no_audio_enabled", True) and not audio_streams:
        issues.append({
            "type": "no_audio",
            "severity": "critical",
            "detail": "",
        })

    # (La detection "no sous-titres" est managede par le module Sous-titres.)

    # 7. File volumineux
    if config.get("large_file_enabled", True):
        max_gb = config.get("max_file_size_gb", 50)
        max_bytes = max_gb * 1024 * 1024 * 1024
        if file_size > max_bytes:
            size_gb = round(file_size / (1024 ** 3), 1)
            issues.append({
                "type": "large_file",
                "severity": "info",
                "detail": f"{size_gb} Go",
            })

    # 8. HDR without fallback (info)
    if config.get("hdr_no_sdr_enabled", True):
        for vs in video_streams:
            vr = (vs.get("VideoRange") or "").upper()
            if vr == "HDR" and len(video_streams) == 1:
                issues.append({
                    "type": "hdr_no_sdr",
                    "severity": "info",
                    "detail": vs.get("VideoRangeType") or "HDR",
                })

    return issues


def _max_severity(issues: list[dict]) -> str:
    """Return the maximum severity across the issues."""
    if any(i["severity"] == "critical" for i in issues):
        return "critical"
    if any(i["severity"] == "warning" for i in issues):
        return "warning"
    if issues:
        return "info"
    return "ok"


def _severity_rank_expr():
    return case(
        (HealthCheckResult.severity == "critical", 0),
        (HealthCheckResult.severity == "warning", 1),
        else_=2,
    )
