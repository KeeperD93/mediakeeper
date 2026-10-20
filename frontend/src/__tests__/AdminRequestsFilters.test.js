/**
 * Admin queue filters: two menus on phones and pills from tablets up (both
 * in the DOM, the stylesheet shows one), plus the "hide available" switch
 * of the all-statuses view.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import AdminRequestsFilters from '@/components/portal/admin/AdminRequestsFilters.vue'

const STATUS_MENU = 'portal.admin.req.statusFilterLabel'
const TYPE_MENU = 'portal.admin.req.typeFilterLabel'

const mountFilters = (props = {}) => mount(AdminRequestsFilters, { props })
const menu = (w, label) => w.find(`select[aria-label="${label}"]`)
const pill = (w, label) => w.findAll('button.arr-pill--filter').find(b => b.text() === label)

describe('AdminRequestsFilters', () => {
  it('offers the same choices in the menus as in the pills', () => {
    const w = mountFilters()
    const values = label =>
      menu(w, label)
        .findAll('option')
        .map(o => o.element.value)

    expect(values(STATUS_MENU)).toEqual(['', 'pending', 'approved', 'available', 'rejected'])
    expect(values(TYPE_MENU)).toEqual(['', 'movie', 'tv'])
    expect(w.findAll('button.arr-pill--filter')).toHaveLength(8)
  })

  it('gives both menus the shared chevron, clear of the right edge', () => {
    const w = mountFilters()

    expect(menu(w, STATUS_MENU).classes()).toContain('mk-select-chevron')
    expect(menu(w, TYPE_MENU).classes()).toContain('mk-select-chevron')
  })

  it('spells out "all types" in the closed menu, where the pill says "All"', () => {
    const w = mountFilters()

    expect(menu(w, TYPE_MENU).find('option').text()).toBe('portal.admin.req.allTypes')
    // A screen reader hears "All types" too, not a second bare "All".
    expect(pill(w, 'portal.admin.req.typeAll').attributes('aria-label')).toBe(
      'portal.admin.req.allTypes',
    )
  })

  it('emits the choice made in a menu', async () => {
    const w = mountFilters()

    await menu(w, STATUS_MENU).setValue('pending')
    await menu(w, TYPE_MENU).setValue('tv')

    expect(w.emitted('update:status')).toEqual([['pending']])
    expect(w.emitted('update:mediaType')).toEqual([['tv']])
  })

  it('emits the choice made with a pill', async () => {
    const w = mountFilters()

    await pill(w, 'portal.requests.rejected').trigger('click')
    await pill(w, 'portal.admin.req.typeMovies').trigger('click')

    expect(w.emitted('update:status')).toEqual([['rejected']])
    expect(w.emitted('update:mediaType')).toEqual([['movie']])
  })

  it('shows the current filters in the menus and the pills', () => {
    const w = mountFilters({ status: 'approved', mediaType: 'movie' })

    expect(menu(w, STATUS_MENU).element.value).toBe('approved')
    expect(menu(w, TYPE_MENU).element.value).toBe('movie')
    expect(pill(w, 'portal.requests.approved').attributes('aria-pressed')).toBe('true')
    expect(pill(w, 'portal.admin.req.typeMovies').attributes('aria-pressed')).toBe('true')
  })

  it('offers the hide switch on the all-statuses view only', async () => {
    const w = mountFilters()

    await w.find('button[role="switch"]').trigger('click')
    expect(w.emitted('update:hideAvailable')).toEqual([[true]])

    await w.setProps({ status: 'pending' })
    expect(w.find('label.arr-switch').exists()).toBe(false)
  })
})
