"""Tests for the Discord-compatible alert payload builder."""
from datetime import datetime

from services.monitoring import AlertType, build_alert_payload
from services.monitoring.payload import MAX_CONTEXT_FIELDS, MAX_FIELD_VALUE_LEN


def test_payload_structure_matches_discord_embed():
    payload = build_alert_payload(
        AlertType.DB_UNAVAILABLE,
        {"consecutive_failures": 2},
        version="0.9.0",
    )

    assert payload["username"] == "MediaKeeper"
    assert isinstance(payload["embeds"], list) and len(payload["embeds"]) == 1
    embed = payload["embeds"][0]
    assert embed["title"] == "Database unavailable"
    assert embed["color"] == 0xE74C3C
    # ISO-8601 timestamp parseable
    datetime.fromisoformat(embed["timestamp"])
    field_names = {f["name"] for f in embed["fields"]}
    assert "version" in field_names
    assert "consecutive_failures" in field_names


def test_payload_truncates_long_context_values():
    long_error = "x" * (MAX_FIELD_VALUE_LEN + 500)
    payload = build_alert_payload(
        AlertType.SCHEDULER_TASK_CRASHED,
        {"error": long_error},
        version="0.9.0",
    )
    error_field = next(f for f in payload["embeds"][0]["fields"] if f["name"] == "error")
    assert len(error_field["value"]) <= MAX_FIELD_VALUE_LEN
    assert error_field["value"].endswith("...")


def test_payload_caps_number_of_context_fields():
    bloated = {f"k{i}": i for i in range(MAX_CONTEXT_FIELDS + 5)}
    payload = build_alert_payload(AlertType.POOL_SATURATED, bloated, version="0.9.0")
    # version + at most MAX_CONTEXT_FIELDS context entries
    assert len(payload["embeds"][0]["fields"]) <= MAX_CONTEXT_FIELDS + 1


def test_recovery_alert_uses_green_color():
    payload = build_alert_payload(AlertType.DB_RECOVERED, None, version="0.9.0")
    assert payload["embeds"][0]["color"] == 0x2ECC71
