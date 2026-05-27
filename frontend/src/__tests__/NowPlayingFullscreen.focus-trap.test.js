/**
 * Covers useFocusTrap wiring on NowPlayingFullscreen — a dismissible
 * fullscreen dialog opened from the dashboard hero. The trap must:
 *   - move focus inside the dialog when it opens,
 *   - emit `close` on Escape,
 *   - expose `role="dialog" aria-modal="true" aria-labelledby="..."`
 *     with the labelledby ID pointing at the rendered <h1>.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiGet,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    apiPatch: vi.fn(),
    apiFetch: vi.fn(),
    loading: { value: false },
    error: { value: null },
  }),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

import NowPlayingFullscreen from '@/components/dashboard/NowPlayingFullscreen.vue'

describe('NowPlayingFullscreen — a11y modal wiring', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue(null)
  })

  it('renders dialog ARIA attributes and links aria-labelledby to the title h1', async () => {
    const w = mount(NowPlayingFullscreen, {
      props: { visible: true, session: { series: 'Foo Show', media: 'Foo Show' } },
      attachTo: document.body,
    })
    await flushPromises()

    const overlay = w.get('.np-overlay')
    expect(overlay.attributes('role')).toBe('dialog')
    expect(overlay.attributes('aria-modal')).toBe('true')

    const labelledby = overlay.attributes('aria-labelledby')
    expect(labelledby).toBeTruthy()

    const title = w.get('.np-title')
    expect(title.attributes('id')).toBe(labelledby)
    expect(title.text()).toBe('Foo Show')

    w.unmount()
  })

  it('emits `close` when Escape is pressed while the modal is open', async () => {
    const w = mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Foo' } },
      attachTo: document.body,
    })
    await w.setProps({ visible: true })
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close')).toHaveLength(1)

    w.unmount()
  })

  it('does not emit `close` on Escape while the modal is hidden', async () => {
    const w = mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Foo' } },
      attachTo: document.body,
    })
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(w.emitted('close')).toBeFalsy()

    w.unmount()
  })

  it('moves focus inside the dialog when it opens', async () => {
    const w = mount(NowPlayingFullscreen, {
      props: { visible: false, session: { series: 'Foo' } },
      attachTo: document.body,
    })
    await w.setProps({ visible: true })
    await flushPromises()

    const overlay = w.get('.np-overlay').element
    // Focus should be on the dialog container (default initial target
    // when no specific focusable is provided to useFocusTrap).
    expect(overlay.contains(document.activeElement)).toBe(true)

    w.unmount()
  })
})
