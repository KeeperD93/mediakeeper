/**
 * The "No effect" label in Settings > Security explains itself: by mouse, by
 * keyboard and by finger, which never "leaves" the label. The explanation sits
 * outside the table so its scroll area cannot cut it off, and always opens
 * towards the roomier half of the screen.
 */
import { afterEach, describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('@/utils/zoom', () => ({ rootZoom: () => 0.5 }))

import SecurityClearedPill from '@/components/settings/security/SecurityClearedPill.vue'

const hint = () => document.body.querySelector('[role="tooltip"]')

let wrapper
function buildPill(rect = { right: 300, top: 100, bottom: 120 }) {
  // The real Teleport (stubbed by the shared setup): leaving the table is the point.
  wrapper = mount(SecurityClearedPill, {
    attachTo: document.body,
    global: { stubs: { Teleport: false } },
  })
  wrapper.element.getBoundingClientRect = () => rect
  return wrapper
}

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
})

describe('SecurityClearedPill', () => {
  it('shows its label, and no explanation until asked', () => {
    const w = buildPill()
    expect(w.text()).toBe('settings.security.cleared')
    expect(hint()).toBeNull()
    expect(w.attributes('aria-describedby')).toBeUndefined()
  })

  it('explains itself while the mouse is on it', async () => {
    const w = buildPill()
    await w.trigger('mouseenter')
    expect(hint().textContent.trim()).toBe('settings.security.clearedHint')
    expect(w.attributes('aria-describedby')).toBe(hint().id)
    expect(w.element.contains(hint())).toBe(false)

    await w.trigger('mouseleave')
    expect(hint()).toBeNull()
    expect(w.attributes('aria-describedby')).toBeUndefined()
  })

  it('explains itself to the keyboard, until the focus leaves or Escape', async () => {
    const w = buildPill()
    await w.trigger('focus')
    expect(hint()).not.toBeNull()
    await w.trigger('blur')
    expect(hint()).toBeNull()

    await w.trigger('focus')
    await w.trigger('keydown', { key: 'Escape' })
    expect(hint()).toBeNull()
  })

  it('stays open under the finger, and a tap elsewhere closes it', async () => {
    const w = buildPill()
    await w.trigger('click')
    w.element.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await w.vm.$nextTick()
    expect(hint()).not.toBeNull()

    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await w.vm.$nextTick()
    expect(hint()).toBeNull()
  })

  it.each([
    ['the page scrolls', () => document.body.dispatchEvent(new Event('scroll'))],
    ['the screen changes size', () => window.dispatchEvent(new Event('resize'))],
  ])('closes when %s, since it cannot follow', async (_, event) => {
    const w = buildPill()
    await w.trigger('mouseenter')
    event()
    await w.vm.$nextTick()
    expect(hint()).toBeNull()
  })

  it('opens below a pill in the top half of the screen', async () => {
    const w = buildPill()
    await w.trigger('mouseenter')
    expect(hint().classList.contains('is-above')).toBe(false)
    expect(hint().style.left).toBe('600px')
    expect(hint().style.top).toBe('240px')
  })

  it('opens above a pill in the bottom half of the screen', async () => {
    const top = window.innerHeight - 40
    const w = buildPill({ right: 300, top, bottom: top + 20 })
    await w.trigger('mouseenter')
    expect(hint().classList.contains('is-above')).toBe(true)
    expect(hint().style.top).toBe(`${top * 2}px`)
  })

  it('leaves nothing behind when the row goes away while open', async () => {
    const remove = vi.spyOn(document, 'removeEventListener')
    const w = buildPill()
    await w.trigger('mouseenter')
    w.unmount()
    wrapper = null
    expect(hint()).toBeNull()
    expect(remove).toHaveBeenCalledWith('pointerdown', expect.any(Function))
    remove.mockRestore()
  })
})
