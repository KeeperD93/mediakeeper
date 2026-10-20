import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return { ...actual, useI18n: () => ({ t: key => key, locale: ref('fr') }) }
})

import AdminRequestsRow from '@/components/portal/admin/AdminRequestsRow.vue'

function mountRow(status, { busy = false } = {}) {
  return mount(AdminRequestsRow, {
    props: { req: { id: 1, tmdb_id: 7, media_type: 'movie', title: 'Sample', status }, busy },
    global: { stubs: { MkAvatar: true } },
  })
}

const action = (w, label) => w.find(`button[aria-label="${label}"]`)
const actionLabels = w => w.findAll('.arr-row-actions button').map(b => b.attributes('aria-label'))

// jsdom has no clipboard API (like http on a LAN address): stub a secure context.
function stubClipboard() {
  const writeText = vi.fn().mockResolvedValue()
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  return writeText
}

describe('AdminRequestsRow actions', () => {
  beforeEach(() => stubClipboard())
  afterEach(() => delete navigator.clipboard)

  it('lets a pending request be approved or rejected', async () => {
    const w = mountRow('pending')

    await action(w, 'portal.admin.approve').trigger('click')
    await action(w, 'portal.admin.reject').trigger('click')

    expect(w.emitted('action')).toEqual([['approved'], ['rejected']])
  })

  it('lets an approved request be marked available or rejected', async () => {
    const w = mountRow('approved')

    await action(w, 'portal.admin.req.markAvailable').trigger('click')
    await action(w, 'portal.admin.reject').trigger('click')

    expect(w.emitted('action')).toEqual([['available'], ['rejected']])
    expect(actionLabels(w)).toEqual([
      'portal.admin.req.markAvailable',
      'portal.admin.reject',
      'portal.admin.delete',
    ])
  })

  it('lets an available request go back to approved, nothing else', async () => {
    const w = mountRow('available')

    await action(w, 'portal.admin.req.undoAvailable').trigger('click')

    expect(w.emitted('action')).toEqual([['approved']])
    expect(actionLabels(w)).toEqual(['portal.admin.req.undoAvailable', 'portal.admin.delete'])
  })

  it.each(['pending', 'approved', 'available', 'rejected'])(
    'can delete a %s request',
    async status => {
      const w = mountRow(status)

      await action(w, 'portal.admin.delete').trigger('click')

      expect(w.emitted('delete')).toHaveLength(1)
    },
  )

  it.each(['pending', 'approved', 'available'])(
    'locks the %s row actions while a call runs, not the title copy',
    status => {
      const w = mountRow(status, { busy: true })

      const actions = w.findAll('.arr-row-actions button')
      expect(actions.length).toBeGreaterThan(1)
      expect(actions.every(b => b.attributes('disabled') !== undefined)).toBe(true)
      expect(w.find('.arr-row-copy').attributes('disabled')).toBeUndefined()
      expect(w.find('article').attributes('aria-busy')).toBe('true')
    },
  )

  it('drops the second click of a double click', () => {
    const w = mountRow('approved')
    // trigger() cannot set the click count: dispatch a real second click.
    const secondClick = () => new MouseEvent('click', { detail: 2, bubbles: true })

    action(w, 'portal.admin.req.markAvailable').element.dispatchEvent(secondClick())
    action(w, 'portal.admin.delete').element.dispatchEvent(secondClick())

    expect(w.emitted('action')).toBeUndefined()
    expect(w.emitted('delete')).toBeUndefined()
  })
})

describe('AdminRequestsRow title copy', () => {
  afterEach(() => delete navigator.clipboard)

  it('copies the title, then says it is copied', async () => {
    const writeText = stubClipboard()
    const w = mountRow('pending')

    await w.find('.arr-row-copy').trigger('click')
    await Promise.resolve()

    expect(writeText).toHaveBeenCalledWith('Sample')
    expect(w.find('.arr-row-copy').attributes('aria-label')).toBe('common.copied')
  })

  it('offers no copy button without a clipboard (not a secure context)', () => {
    expect(mountRow('pending').find('.arr-row-copy').exists()).toBe(false)
  })
})
