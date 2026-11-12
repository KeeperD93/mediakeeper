/**
 * A failed scheduler run is named by a translated sentence carrying the
 * exception class the server stored, in the row tooltip and in its menu.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

import SchedulerTaskRow from '@/components/settings/SchedulerTaskRow.vue'
import SchedulerTaskRowMenu from '@/components/settings/SchedulerTaskRowMenu.vue'

const TASK = {
  key: 'watchlist_scan',
  label: 'Watchlist scan',
  label_key: '',
  description: 'scheduler.watchlist_check',
  enabled: true,
  interval_sec: 3600,
  default_sec: 3600,
  last_run: null,
  last_status: 'error',
  last_error: 'TimeoutError',
  run_count: 2,
  progress: null,
}
// The global $t mock serialises params as `key:{json}`.
const DETAIL = 'scheduler.lastErrorDetail:{"type":"TimeoutError"}'
const noop = () => {}

describe('Scheduler last error', () => {
  it('shows the translated sentence as the row tooltip', () => {
    const w = mount(SchedulerTaskRow, {
      props: {
        task: TASK,
        schedEditValues: {},
        intervalToAmount: () => 1,
        formatSeconds: () => '1h',
        formatRunDate: () => '',
        schedStatusDot: () => 'dot-error',
        schedIsDirty: () => false,
        schedToggle: noop,
        schedSaveInterval: noop,
        schedReset: noop,
        schedRunNow: noop,
        schedOnAmountChange: noop,
        schedOnUnitChange: noop,
      },
    })
    expect(w.get('.str-meta-error').attributes('title')).toBe(DETAIL)
    w.unmount()
  })

  it('shows the translated sentence in the task menu', () => {
    const w = mount(SchedulerTaskRowMenu, { props: { task: TASK, formatSeconds: () => '1h' } })
    expect(w.get('.strm-error-body').text()).toBe(DETAIL)
    w.unmount()
  })
})
