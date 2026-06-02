"""Retrieve Emby logs via the API and dedupe."""
from ._config import EMBY_LOG, LOG_DIR, logger
from ._files import write_log_line


async def fetch_and_store_emby_logs(db):
    """
    Fetch les logs Emby via l'API et les writes in emby.txt.
    Avoid les duplicates en gardant trace du last log saved.
    """
    from services.emby import get_activity_logs

    try:
        logs = await get_activity_logs(db, limit=50)
        if not logs:
            return

        emby_path = LOG_DIR / EMBY_LOG
        existing_lines = set()
        if emby_path.is_file():
            try:
                with open(emby_path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    for line in all_lines[-200:]:
                        existing_lines.add(line.strip())
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass

        new_count = 0
        for log in reversed(logs):
            date = log.get("date", "")[:19].replace("T", " ")
            severity = log.get("severity", "Info")
            name = log.get("name", "")
            user = log.get("user", "")
            user_part = f" [{user}]" if user else ""

            line = f"{date} [{severity}]{user_part} {name}"
            if line not in existing_lines:
                write_log_line("emby", f"[{severity}]{user_part} {name}")
                new_count += 1

        if new_count > 0:
            logger.debug("Emby logs : %s new entries written", new_count)

    except Exception as e:
        logger.error("Error fetch_and_store_emby_logs: %s", e)
