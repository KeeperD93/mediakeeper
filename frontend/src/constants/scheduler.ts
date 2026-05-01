/**
 * Scheduler task run-status, consumed by ParamsTestTab / NotificationsView
 * and the status dot in the scheduler list. Mirrors the `last_status`
 * column on the `scheduler_tasks` table.
 *
 * Note: `ok` and `error` are the canonical outcomes written by the task
 * runner; `failed` is emitted by the webhook delivery subsystem on
 * non-2xx responses. Both flavours are kept here so any consumer can
 * compare against the whole namespace without redeclaring magic strings.
 */
export const TASK_STATUS = Object.freeze({
  RUNNING: 'running',
  OK: 'ok',
  ERROR: 'error',
  FAILED: 'failed',
} as const)

export type TaskStatus = (typeof TASK_STATUS)[keyof typeof TASK_STATUS]
