"""Helpers shareds : parsing de dates Emby, detection DND, mapping events."""
from datetime import datetime, time as dtime, timezone

# Event -> template key mapping (used by send_system_notification)
EVENT_TO_TPL = {
    "offline":             "server_offline",
    "duplicate":           "duplicate_found",
    "new_request":         "request_new",
    "request_approved":    "request_approved",
    "request_available":   "request_available",
    "partially_available": "request_partial",
    "request_rejected":    "request_rejected",
    "new_issue":           "issue_new",
    "issue_comment":       "issue_comment",
    "issue_resolved":      "issue_resolved",
    "emby_alerts":         "emby_alert",
}


def _parse_date(s: str):
    """Parse une date ISO Emby en datetime UTC — robuste aux formats variables."""
    if not s:
        return None
    s = s.rstrip("Z").split(".")[0]
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _is_dnd(rules: dict) -> bool:
    """Return True when in Do Not Disturb mode (local time range)."""
    if not rules.get("dnd_enabled"):
        return False
    now_local = datetime.now().time().replace(second=0, microsecond=0)
    try:
        dnd_start = dtime.fromisoformat(rules.get("dnd_start", "23:00"))
        dnd_end   = dtime.fromisoformat(rules.get("dnd_end",   "07:00"))
        if dnd_start <= dnd_end:
            return dnd_start <= now_local <= dnd_end
        return now_local >= dnd_start or now_local <= dnd_end  # chevauchement minuit
    except Exception:
        return False
