import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h, ref, type Ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useFocusTrap } from '@/composables/useFocusTrap'

interface HarnessRefs {
  active: Ref<boolean>
}

function buildHarness({ useInitial = false, focusable = true } = {}) {
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
        { ref: 'containerRef', tabindex: focusable ? -1 : undefined, 'data-testid': 'container' },
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

  it('wraps Shift+Tab from the container itself to the last focusable', async () => {
    const { wrapper, refs } = buildHarness()
    refs.active.value = true
    await flushPromises()
    const last = wrapper.find('[data-testid="last"]').element as HTMLButtonElement
    expect(document.activeElement).toBe(wrapper.find('[data-testid="container"]').element)
    const shiftTab = new KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(shiftTab)
    expect(shiftTab.defaultPrevented).toBe(true)
    expect(document.activeElement).toBe(last)
    wrapper.unmount()
  })

  it('makes a container without tabindex focusable, out of the Tab order', async () => {
    const { wrapper, refs } = buildHarness({ useInitial: true, focusable: false })
    const container = wrapper.find('[data-testid="container"]').element
    expect(container.hasAttribute('tabindex')).toBe(false)
    refs.active.value = true
    await flushPromises()
    expect(container.getAttribute('tabindex')).toBe('-1')
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

describe('useFocusTrap, focus out of the Tab order inside the panel', () => {
  // A title given the focus (tabindex -1), controls, a note between them and one after.
  function buildPanel() {
    const Panel = defineComponent({
      setup() {
        const containerRef = ref<HTMLElement | null>(null)
        useFocusTrap({ active: ref(true), containerRef })
        return { containerRef }
      },
      render() {
        return h('div', { ref: 'containerRef', tabindex: -1 }, [
          h('h2', { tabindex: -1, 'data-testid': 'title' }, 'title'),
          h('button', { 'data-testid': 'first' }, 'first'),
          h('p', { tabindex: -1, 'data-testid': 'between' }, 'between'),
          h('button', { 'data-testid': 'last' }, 'last'),
          h('p', { tabindex: -1, 'data-testid': 'after' }, 'after'),
        ])
      },
    })
    return mount(Panel, { attachTo: document.body })
  }

  function tab(from: Element, shiftKey: boolean): KeyboardEvent {
    ;(from as HTMLElement).focus()
    const event = new KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey,
      bubbles: true,
      cancelable: true,
    })
    document.dispatchEvent(event)
    return event
  }

  const el = (wrapper: ReturnType<typeof buildPanel>, id: string) =>
    wrapper.find(`[data-testid="${id}"]`).element

  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('wraps Shift+Tab from a title before the first control to the last one', async () => {
    const wrapper = buildPanel()
    await flushPromises()

    const event = tab(el(wrapper, 'title'), true)

    expect(event.defaultPrevented).toBe(true)
    expect(document.activeElement).toBe(el(wrapper, 'last'))
    wrapper.unmount()
  })

  it('wraps Tab from an element after the last control to the first one', async () => {
    const wrapper = buildPanel()
    await flushPromises()

    const event = tab(el(wrapper, 'after'), false)

    expect(event.defaultPrevented).toBe(true)
    expect(document.activeElement).toBe(el(wrapper, 'first'))
    wrapper.unmount()
  })

  it('leaves the moves that stay inside to the browser', async () => {
    const wrapper = buildPanel()
    await flushPromises()

    expect(tab(el(wrapper, 'title'), false).defaultPrevented).toBe(false)
    expect(tab(el(wrapper, 'between'), true).defaultPrevented).toBe(false)
    expect(tab(el(wrapper, 'between'), false).defaultPrevented).toBe(false)
    wrapper.unmount()
  })
})
