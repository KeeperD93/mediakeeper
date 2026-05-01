"""Weekly rotation + cleanup of old archived files."""
from datetime import datetime, timedelta, timezone

from ._config import (
    EMBY_LOG,
    LOG_DIR,
    MAX_LOG_FILES,
    MAX_LOG_LINES,
    MEDIAKEEPER_LOG,
    ensure_log_dir,
    logger,
)


def _cleanup_old_log_files(base_name: str):
    """Supprime les files d'archive les plus anciens si on exceeds MAX_LOG_FILES."""
    ensure_log_dir()
    archives = sorted(
        [f for f in LOG_DIR.iterdir() if f.is_file() and f.name.startswith(base_name + "_") and f.suffix == ".txt"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for old_file in archives[MAX_LOG_FILES - 1:]:
        try:
            old_file.unlink()
            logger.info(f"Ancien log deleted : {old_file.name}")
        except Exception as e:
            logger.error(f"Error deletion {old_file.name}: {e}")


def rotate_logs_if_needed():
    """
    Rotation des logs :
    - Si le file actif a plus de 7 jours
    - OU si le file exceeds 30 000 lines
    Le rename with la range de dates et creater un new file.
    Called at startup and periodically.
    """
    ensure_log_dir()
    now = datetime.now(timezone.utc)

    for active_name in [MEDIAKEEPER_LOG, EMBY_LOG]:
        filepath = LOG_DIR / active_name
        if not filepath.is_file():
            continue

        stat = filepath.stat()
        created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        marker_path = LOG_DIR / f".{active_name}.start"
        if marker_path.is_file():
            try:
                start_date = datetime.fromisoformat(marker_path.read_text().strip())
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
            except Exception:
                start_date = created
        else:
            start_date = created

        age_days = (now - start_date).days
        needs_rotate = age_days >= 7

        if not needs_rotate:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    line_count = sum(1 for _ in f)
                if line_count >= MAX_LOG_LINES:
                    needs_rotate = True
                    logger.info(f"Rotation {active_name} : {line_count} lines (max {MAX_LOG_LINES})")
            except Exception:
                pass

        if needs_rotate:
            end_date = now - timedelta(days=1)
            base_name = active_name.replace(".txt", "")
            archive_name = f"{base_name}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.txt"
            archive_path = LOG_DIR / archive_name

            counter = 1
            while archive_path.is_file():
                archive_name = f"{base_name}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}_{counter}.txt"
                archive_path = LOG_DIR / archive_name
                counter += 1

            try:
                filepath.rename(archive_path)
                logger.info(f"Log rotated : {active_name} → {archive_name}")
                _cleanup_old_log_files(base_name)
            except Exception as e:
                logger.error(f"Error rotation {active_name}: {e}")
                continue

            filepath.touch()
            marker_path.write_text(now.isoformat())
        elif not marker_path.is_file():
            marker_path.write_text(start_date.isoformat())
