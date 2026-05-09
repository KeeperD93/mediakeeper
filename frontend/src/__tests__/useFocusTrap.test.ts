import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h, ref, type Ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useFocusTrap } from '@/composables/useFocusTrap'

interface HarnessRefs {
  active: Ref<boolean>
}

function buildHarness({ useInitial = false } = {}) {
  const onEscape = vi.fn()
  const refs = {} as HarnessRefs
  const Harness = defineComponent({
    setup() {
      const active = ref(false)
      const containerRef = ref<HTMLElement | null>(null)
      const initialRef = ref<HTMLElement | null>(null)
      refs.active = active
      useFocusTrap({
        active,
        containerRef,
        onEscape,
        initialFocusRef: useInitial ? initialRef : undefined,
      })
      return { containerRef, initialRef }
    },
    render() {
      return h(
        'div',
        { ref: 'containerRef', tabindex: -1, 'data-testid': 'container' },
        [
          h(
            'button',
            { ref: useInitial ? 'initialRef' : undefined, 'data-testid': 'first' },
            'first',
          ),
          h('button', { 'data-testid': 'middle' }, 'middle'),
          h('button', { 'data-testid': 'last' }, 'last'),
        ],
      )
    },
  })
  const wrapper = mount(Harness, { attachTo: document.body })
  return { wrapper, onEscape, refs }
}

describe('useFocusTrap', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('focuses initialFocusRef on activation when provided', async () => {
    const { wrapper, refs } = buildHarness({ useInitial: true })
    refs.active.value = true
    await flushPromises()
    expect(document.activeElement).toBe(wrapper.find('[data-testid="first"]').element)
    wrapper.unmount()
  })

  it('focuses container on activation when no initialFocusRef', async () => {
    const { wrapper, refs } = buildHarness({ useInitial: false })
    refs.active.value = true
    await flushPromises()
    expect(document.activeElement).toBe(wrapper.find('[data-testid="container"]').element)
    wrapper.unmount()
  })

  it('returns focus to previously focused element on deactivate', async () => {
    const trigger = document.createElement('button')
    trigger.textContent = 'trigger'
    document.body.appendChild(trigger)
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    const { wrapper, refs } = buildHarness({ useInitial: true })
    refs.active.value = true
    await flushPromises()
    expect(document.activeElement).not.toBe(trigger)

    refs.active.value = false
    await flushPromises()
    expect(document.activeElement).toBe(trigger)

    wrapper.unmount()
    trigger.remove()
  })

  it('calls onEscape on Escape key without modifier', async () => {
    const { wrapper, onEscape, refs } = buildHarness()
    refs.active.value = true
    await flushPromises()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(onEscape).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('wraps Tab from last focusable to first', async () => {
    const { wrapper, refs } = buildHarness()
    refs.active.value = true
    await flushPromises()
    const first = wrapper.find('[data-testid="first"]').element as HTMLButtonElement
    const last = wrapper.find('[data-testid="last"]').element as HTMLButtonElement
    last.focus()
    expect(document.activeElement).toBe(last)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(first)
    wrapper.unmount()
  })

  it('wraps Shift+Tab from first focusable to last', async () => {
    const { wrapper, refs } = buildHarness()
    refs.active.value = true
    await flushPromises()
    const first = wrapper.find('[data-testid="first"]').element as HTMLButtonElement
    const last = wrapper.find('[data-testid="last"]').element as HTMLButtonElement
    first.focus()
    expect(document.activeElement).toBe(first)
    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
    )
    expect(document.activeElement).toBe(last)
    wrapper.unmount()
  })

  it('detaches the keydown listener on unmount', async () => {
    const { wrapper, onEscape, refs } = buildHarness()
    refs.active.value = true
    await flushPromises()
    wrapper.unmount()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(onEscape).not.toHaveBeenCalled()
  })
})
