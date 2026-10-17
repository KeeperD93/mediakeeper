/**
 * Retention bounds of the backup settings, mirrored from the backend
 * (`RetentionRequest.days` in `api/backup/_schemas.py`): 1 to 365 days, or
 * the last 1 to 100 backups, stored as a negative number of days.
 */
export const BACKUP_RETENTION_MAX_DAYS = 365
export const BACKUP_RETENTION_MAX_COUNT = 100
