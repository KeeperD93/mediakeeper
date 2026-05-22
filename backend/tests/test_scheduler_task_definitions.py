"""Coherence checks on TASK_DEFINITIONS — guards against missing i18n keys."""
from services.scheduler._tasks import TASK_DEFINITIONS


def test_every_task_has_label_key():
    """Every task definition must expose an i18n label key so the frontend
    can render a translated name. A missing label_key would silently fall
    back to the English ``label`` string."""
    missing = [k for k, defn in TASK_DEFINITIONS.items() if not defn.get("label_key")]
    assert not missing, f"Tasks without label_key: {missing}"


def test_label_keys_follow_namespace_convention():
    """Label keys live under ``scheduler.tasks.<task_key>`` to keep the
    locale namespace tidy and predictable."""
    for key, defn in TASK_DEFINITIONS.items():
        expected = f"scheduler.tasks.{key}"
        assert defn["label_key"] == expected, (
            f"Task {key!r} has label_key={defn['label_key']!r}, expected {expected!r}"
        )


def test_label_and_description_present():
    """Both legacy ``label`` (EN fallback) and ``description`` (i18n key)
    are still required — the frontend uses ``label`` as graceful fallback
    when ``$t(label_key)`` returns the key itself."""
    for key, defn in TASK_DEFINITIONS.items():
        assert defn.get("label"), f"Task {key!r} missing label"
        assert defn.get("description"), f"Task {key!r} missing description"
