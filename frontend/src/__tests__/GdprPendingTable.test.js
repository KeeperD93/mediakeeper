/**
 * Vitest coverage for the pending-deletion table.
 *
 * Three states: empty, loading, populated. The cancel button emits
 * the row payload upstream — Phase 11B.2 wires the API call in the
 * GdprSection composition root.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/i18n', () => ({ getLocale: () => 'fr' }))

import GdprPendingTable from '@/components/portal/admin/GdprPendingTable.vue'

describe('GdprPendingTable', () => {
  it('renders the empty state when no rows are provided', () => {
    const w = mount(GdprPendingTable, { props: { rows: [], loading: false } })
    expect(w.find('.pt-gdpr-pending-empty').exists()).toBe(true)
    expect(w.find('table').exists()).toBe(false)
  })

  it('renders the loading state when loading=true', () => {
    const w = mount(GdprPendingTable, { props: { rows: [], loading: true } })
    expect(w.find('.pt-gdpr-pending-loading').exists()).toBe(true)
  })

  it('renders one table row per pending user', () => {
    const w = mount(GdprPendingTable, {
      props: {
        rows: [
          {
            id: 1,
            username: 'alice',
            deletion_requested_at: '2026-05-01T12:00:00+00:00',
            pending_deletion_at: '2026-05-31T12:00:00+00:00',
          },
          {
            id: 2,
            username: 'bob',
            deletion_requested_at: '2026-05-02T12:00:00+00:00',
            pending_deletion_at: '2026-06-01T12:00:00+00:00',
          },
        ],
      },
    })
    const rows = w.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('alice')
    expect(rows[1].text()).toContain('bob')
  })

  it('emits "cancel" with the full row when the per-row button is clicked', async () => {
    const row = {
      id: 42,
      username: 'carol',
      deletion_requested_at: '2026-05-03T08:00:00+00:00',
      pending_deletion_at: '2026-06-02T08:00:00+00:00',
    }
    const w = mount(GdprPendingTable, { props: { rows: [row] } })
    await w.find('.pt-gdpr-pending-cancel').trigger('click')
    const emitted = w.emitted('cancel')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toEqual(row)
  })

  it('disables the cancel button while a cancel is in-flight for that row', () => {
    const w = mount(GdprPendingTable, {
      props: {
        rows: [
          {
            id: 7,
            username: 'dave',
            deletion_requested_at: '2026-05-03T08:00:00+00:00',
            pending_deletion_at: '2026-06-02T08:00:00+00:00',
          },
        ],
        cancellingId: 7,
      },
    })
    expect(w.find('.pt-gdpr-pending-cancel').attributes('disabled')).toBeDefined()
  })

  it('emits "refresh" when the refresh button is clicked', async () => {
    const w = mount(GdprPendingTable, { props: { rows: [], loading: false } })
    await w.find('.pt-gdpr-pending-refresh').trigger('click')
    expect(w.emitted('refresh')).toBeTruthy()
  })

  it('flags rows whose scheduled date has already lapsed', () => {
    // Use a date safely in the past so the test is deterministic.
    const past = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    const future = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()

    const w = mount(GdprPendingTable, {
      props: {
        rows: [
          { id: 1, username: 'late', deletion_requested_at: past, pending_deletion_at: past },
          { id: 2, username: 'early', deletion_requested_at: past, pending_deletion_at: future },
        ],
      },
    })
    const overdueCells = w.findAll('.pt-gdpr-pending-scheduled--overdue')
    expect(overdueCells).toHaveLength(1)
  })
})
