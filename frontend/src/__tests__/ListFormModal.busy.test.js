/**
 * The list form sends once: Save is off while the page saves, and a click
 * during the closing fade (form already closed) sends nothing.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))

import ListFormModal from '@/components/portal/lists/ListFormModal.vue'

const mountForm = props =>
  mount(ListFormModal, {
    props: { initial: { name: 'My list' }, ...props },
    attachTo: document.body,
  })

describe('ListFormModal — one send', () => {
  it('turns Save off and sends nothing while the page saves', async () => {
    const w = mountForm({ open: true, busy: true })
    const save = w.find('.lfm-btn--primary')

    expect(save.attributes('disabled')).toBeDefined()
    await save.trigger('click')

    expect(w.emitted('submit')).toBeUndefined()
    w.unmount()
  })

  it('sends nothing once closed, during its closing fade', async () => {
    const w = mountForm({ open: true })
    const save = w.find('.lfm-btn--primary').element
    await w.setProps({ open: false })

    // The fading button is still clickable for a moment.
    save.dispatchEvent(new MouseEvent('click'))

    expect(w.emitted('submit')).toBeUndefined()
    w.unmount()
  })

  it('sends the form when open and idle', async () => {
    const w = mountForm({ open: true })

    await w.find('.lfm-btn--primary').trigger('click')

    expect(w.emitted('submit')).toHaveLength(1)
    w.unmount()
  })
})
