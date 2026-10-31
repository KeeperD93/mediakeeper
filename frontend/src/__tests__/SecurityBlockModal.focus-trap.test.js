/**
 * Covers the add-block dialog of Settings > Security: focus starts on the IP
 * field and stays in the dialog, Escape closes it except while a save is on
 * its way, and a block is always sent as permanent with a scope from the list.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { TOAST_TYPE } from '@/constants/toast'

const showToast = vi.hoisted(() => vi.fn())

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

import SecurityBlockModal from '@/components/settings/security/SecurityBlockModal.vue'

function buildModal(props = {}) {
  return mount(SecurityBlockModal, {
    props: { busy: false, scopeLabel: scope => `scope:${scope}`, ...props },
    attachTo: document.body,
  })
}

const escape = () =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))

describe('SecurityBlockModal — focus trap integration', () => {
  beforeEach(() => showToast.mockClear())

  it('is a labelled dialog that moves focus onto the IP field', async () => {
    const w = buildModal()
    await flushPromises()

    const dialog = w.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(w.get(`#${dialog.attributes('aria-labelledby')}`).text()).toBe(
      'settings.security.addBlock',
    )
    expect(document.activeElement).toBe(w.get('input').element)
    w.unmount()
  })

  it('wraps Tab from the last control back to the first', async () => {
    const w = buildModal()
    await flushPromises()

    w.get('button[type="submit"]').element.focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(w.get('input').element)
    w.unmount()
  })

  it('wraps Shift+Tab from the IP field to Save', async () => {
    const w = buildModal()
    await flushPromises()

    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
    )
    expect(document.activeElement).toBe(w.get('button[type="submit"]').element)
    w.unmount()
  })

  it('routes Escape to close exactly once', async () => {
    const w = buildModal()
    await flushPromises()

    escape()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })

  it('gives focus back to the control that opened it', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const w = buildModal()
    await flushPromises()
    expect(document.activeElement).not.toBe(opener)

    w.unmount()
    await flushPromises()
    expect(document.activeElement).toBe(opener)
    opener.remove()
  })

  it('ignores Escape, Cancel and the backdrop while a save is on its way', async () => {
    const w = buildModal({ busy: true })
    await flushPromises()

    escape()
    await w.get('[role="dialog"]').trigger('click')
    await w.get('button[type="button"]').trigger('click')
    expect(w.emitted('close')).toBeUndefined()
    expect(w.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    w.unmount()
  })

  it('offers the manual scopes with their labels and the shared chevron', async () => {
    const w = buildModal()
    const select = w.get('select')

    expect(select.classes()).toContain('mk-select-chevron')
    expect(select.findAll('option').map(o => [o.element.value, o.text()])).toEqual([
      ['all', 'scope:all'],
      ['admin', 'scope:admin'],
      ['portal', 'scope:portal'],
    ])
    w.unmount()
  })

  it('sends a permanent block, and nothing without an IP or a name', async () => {
    const w = buildModal()

    await w.get('form').trigger('submit')
    expect(w.emitted('submit')).toBeUndefined()
    expect(showToast).toHaveBeenCalledWith('settings.security.needIpOrUser', TOAST_TYPE.ERR)

    await w.get('input').setValue(' 203.0.113.7 ')
    await w.get('select').setValue('portal')
    await w.get('form').trigger('submit')
    expect(w.emitted('submit')[0][0]).toEqual({
      ip: '203.0.113.7',
      username: '',
      scope: 'portal',
      reason: '',
      permanent: true,
    })
    w.unmount()
  })
})
