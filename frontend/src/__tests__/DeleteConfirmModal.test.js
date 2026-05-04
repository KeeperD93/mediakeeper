/**
 * Vitest coverage for the destructive deletion confirmation modal.
 *
 * The confirm button stays disabled until the user types the magic
 * word EXACTLY (case-sensitive). Cancel emits ``cancel`` and is
 * suppressed while the parent reports ``submitting``.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    // Return a deterministic magic word so the test compares against
    // a known string without coupling to fr.json's actual text.
    t: (key) => (key === 'portal.privacy.deleteModal.magicWord' ? 'SUPPRIMER' : key),
  }),
}))

vi.mock('lucide-vue-next', () => ({
  AlertTriangle: { name: 'AlertTriangleStub', template: '<i />' },
}))

import DeleteConfirmModal from '@/components/portal/settings/DeleteConfirmModal.vue'


function buildModal(props = {}) {
  return mount(DeleteConfirmModal, {
    props: { open: true, ...props },
    global: {
      stubs: {
        'i18n-t': { template: '<span><slot name="word"/></span>' },
      },
    },
  })
}


describe('DeleteConfirmModal', () => {
  it('does not render when closed', () => {
    const w = buildModal({ open: false })
    expect(w.find('.pt-dcm-panel').exists()).toBe(false)
  })

  it('renders the panel when open', async () => {
    const w = buildModal()
    await flushPromises()
    expect(w.find('.pt-dcm-panel').exists()).toBe(true)
    expect(w.find('.pt-dcm-input').exists()).toBe(true)
  })

  it('keeps the confirm button disabled until the magic word is typed', async () => {
    const w = buildModal()
    await flushPromises()

    const confirmBtn = w.find('.pt-dcm-btn--danger')
    expect(confirmBtn.attributes('disabled')).toBeDefined()

    const input = w.find('.pt-dcm-input')
    await input.setValue('supprimer') // wrong case
    expect(confirmBtn.attributes('disabled')).toBeDefined()

    await input.setValue('SUPPRIMER')
    await flushPromises()
    expect(confirmBtn.attributes('disabled')).toBeUndefined()
  })

  it('emits "confirm" only when the magic word is typed', async () => {
    const w = buildModal()
    await flushPromises()
    const confirmBtn = w.find('.pt-dcm-btn--danger')

    await confirmBtn.trigger('click')
    expect(w.emitted('confirm')).toBeFalsy()

    await w.find('.pt-dcm-input').setValue('SUPPRIMER')
    await confirmBtn.trigger('click')
    expect(w.emitted('confirm')).toBeTruthy()
  })

  it('emits "cancel" on the abort button', async () => {
    const w = buildModal()
    await flushPromises()
    await w.findAll('.pt-dcm-btn')[0].trigger('click')
    expect(w.emitted('cancel')).toBeTruthy()
  })

  it('does not emit "cancel" while submitting', async () => {
    const w = buildModal({ submitting: true })
    await flushPromises()
    await w.findAll('.pt-dcm-btn')[0].trigger('click')
    expect(w.emitted('cancel')).toBeFalsy()
  })

  it('renders the Emby notice when showEmbyNotice is true', async () => {
    const w = buildModal({ showEmbyNotice: true })
    await flushPromises()
    expect(w.find('.pt-dcm-emby').exists()).toBe(true)
  })

  it('hides the Emby notice by default (local accounts)', async () => {
    const w = buildModal()
    await flushPromises()
    expect(w.find('.pt-dcm-emby').exists()).toBe(false)
  })
})
