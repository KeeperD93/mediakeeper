/**
 * Retention bounds of the backup settings, mirrored from the backend
 * (`RetentionRequest.days` in `api/backup/_schemas.py`): 1 to 365 days, or
 * the last 1 to 100 backups, stored as a negative number of days.
 */
export const BACKUP_RETENTION_MAX_DAYS = 365
export const BACKUP_RETENTION_MAX_COUNT = 100

/** How the backups are pruned: by age, by number kept, or never. */
export const BACKUP_RETENTION_MODE = Object.freeze({
  DAYS: 'days',
  COUNT: 'count',
  OFF: 'off',
} as const)

export type BackupRetentionMode = (typeof BACKUP_RETENTION_MODE)[keyof typeof BACKUP_RETENTION_MODE]
