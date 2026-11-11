"""A restore must not leave this installation with secrets it cannot read."""
import logging

from core.encryption import ENCRYPTED_PREFIX, can_decrypt

logger = logging.getLogger("mediakeeper.backup")


class BackupKeyMismatchError(Exception):
    """Raised before anything is written: the active key reads none of the backup's secrets."""


def is_unreadable_secret(value: object) -> bool:
    """True for a value the active key cannot read: writing it would blank what it replaces."""
    return isinstance(value, str) and not can_decrypt(value)


def check_restored_secrets(plan: list[tuple[str, object, object]], results: dict) -> None:
    """Refuse a settings part when none of its secrets reads with the active key.

    A value that reads makes a key mismatch unlikely, not impossible: the unreadable
    ones are skipped either way (see ``is_unreadable_secret``) and counted in ``results``.
    """
    settings = next((payload for part, payload, _ in plan if part == "settings"), None)
    if not isinstance(settings, dict):
        return  # its handler reports a malformed part
    secrets = [v for v in settings.values() if isinstance(v, str) and v.startswith(ENCRYPTED_PREFIX)]
    unreadable = sum(is_unreadable_secret(v) for v in secrets)
    if secrets and unreadable == len(secrets):
        logger.warning("[backup] Restore refused: the active key reads none of its %d secrets", len(secrets))
        raise BackupKeyMismatchError
    if unreadable:
        logger.warning("[backup] Restore skips %d unreadable secret(s), current values left unchanged", unreadable)
        results["secrets_skipped"] = unreadable
