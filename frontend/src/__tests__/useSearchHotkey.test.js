/**
 * Covers the global Ctrl/Cmd+K shortcut composable: focus delegation,
 * cleanup on unmount, and skip rule for editable targets.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

import { useSearchHotkey } from '@/composables/portal/useSearchHotkey'

function buildHarness(focusFn) {
  return mount(
    defineComponent({
      setup() {
        useSearchHotkey(focusFn)
        return () => h('div')
      },
    }),
  )
}

function dispatchCmdK(target = document, init = {}) {
  const event = new KeyboardEvent('keydown', {
    key: 'k',
    ctrlKey: true,
    bubbles: true,
    cancelable: true,
    ...init,
  })
  target.dispatchEvent(event)
  return event
}

beforeEach(() => {
  document.body.innerHTML = ''
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('useSearchHotkey', () => {
  it('invokes the callback and prevents default on Ctrl+K from a non-text target', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    const event = dispatchCmdK(document.body)

    expect(focus).toHaveBeenCalledTimes(1)
    expect(event.defaultPrevented).toBe(true)
    w.unmount()
  })

  it('invokes the callback on Cmd+K (macOS)', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    const event = new KeyboardEvent('keydown', {
      key: 'k',
      metaKey: true,
      bubbles: true,
      cancelable: true,
    })
    document.body.dispatchEvent(event)

    expect(focus).toHaveBeenCalledTimes(1)
    w.unmount()
  })

  it('does not intercept when the event target is an input', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    const input = document.createElement('input')
    input.type = 'text'
    document.body.appendChild(input)
    input.focus()

    const event = dispatchCmdK(input)

    expect(focus).not.toHaveBeenCalled()
    expect(event.defaultPrevented).toBe(false)
    w.unmount()
  })

  it('does not intercept when the event target is a textarea', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    const textarea = document.createElement('textarea')
    document.body.appendChild(textarea)
    textarea.focus()

    dispatchCmdK(textarea)

    expect(focus).not.toHaveBeenCalled()
    w.unmount()
  })

  it('does not intercept when the event target is a contenteditable element', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    const editable = document.createElement('div')
    editable.setAttribute('contenteditable', 'true')
    document.body.appendChild(editable)

    dispatchCmdK(editable)

    expect(focus).not.toHaveBeenCalled()
    w.unmount()
  })

  it('removes the listener on unmount', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    w.unmount()

    dispatchCmdK(document.body)
    expect(focus).not.toHaveBeenCalled()
  })

  it('ignores keys other than k', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    document.body.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'j', ctrlKey: true, bubbles: true }),
    )

    expect(focus).not.toHaveBeenCalled()
    w.unmount()
  })

  it('ignores plain k without modifier', () => {
    const focus = vi.fn()
    const w = buildHarness(focus)

    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', bubbles: true }))

    expect(focus).not.toHaveBeenCalled()
    w.unmount()
  })
})
