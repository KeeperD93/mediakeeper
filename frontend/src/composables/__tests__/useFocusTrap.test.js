/**
 * useFocusTrap — the shared focus-trap behind every Media Manager (and other)
 * dialog. Covers the §23.6 contract: Tab wraps in both directions, Escape
 * triggers the close callback, focus moves into the dialog on activation and is
 * restored to the opener on deactivation.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref, nextTick } from 'vue'
import { mount } from '@vue/test-utils'

import { useFocusTrap } from '@/composables/useFocusTrap'

let host = null

function makeHost({ active = ref(true), onEscape } = {}) {
  const captured = { active }
  const Host = defineComponent({
    setup() {
      const panelRef = ref(null)
      const firstRef = ref(null)
      captured.panelRef = panelRef
      useFocusTrap({ active, containerRef: panelRef, initialFocusRef: firstRef, onEscape })
      return () =>
        h('div', [
          h('button', { class: 'outside' }, 'outside'),
          h('div', { ref: panelRef, tabindex: '-1', class: 'panel' }, [
            h('button', { ref: firstRef, class: 'first' }, 'first'),
            h('button', { class: 'mid' }, 'mid'),
            h('button', { class: 'last' }, 'last'),
          ]),
        ])
    },
  })
  host = mount(Host, { attachTo: document.body })
  return captured
}

function keydown(init) {
  document.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, ...init }))
}

const q = sel => document.querySelector(sel)

afterEach(() => {
  host?.unmount()
  host = null
})

describe('useFocusTrap', () => {
  it('moves focus to the initial element on activation', async () => {
    makeHost()
    await nextTick()
    await nextTick()
    expect(document.activeElement).toBe(q('.first'))
  })

  it('calls onEscape when Escape is pressed', async () => {
    const onEscape = vi.fn()
    makeHost({ onEscape })
    await nextTick()
    keydown({ key: 'Escape' })
    expect(onEscape).toHaveBeenCalledTimes(1)
  })

  it('wraps Tab from the last element back to the first', async () => {
    makeHost()
    await nextTick()
    q('.last').focus()
    keydown({ key: 'Tab' })
    expect(document.activeElement).toBe(q('.first'))
  })

  it('wraps Shift+Tab from the first element to the last', async () => {
    makeHost()
    await nextTick()
    q('.first').focus()
    keydown({ key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(q('.last'))
  })

  it('restores focus to the opener on deactivation', async () => {
    const active = ref(false)
    makeHost({ active })
    await nextTick()
    q('.outside').focus()
    expect(document.activeElement).toBe(q('.outside'))

    active.value = true
    await nextTick()
    await nextTick()
    expect(document.activeElement).toBe(q('.first'))

    active.value = false
    await nextTick()
    await nextTick()
    expect(document.activeElement).toBe(q('.outside'))
  })
})
