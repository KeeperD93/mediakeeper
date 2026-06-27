/**
 * Vitest coverage for the rectangle lasso composable.
 *
 * The lasso is wired by the Media Manager file list. Tests focus on
 * the behaviour the file list relies on: mouse-down on empty space
 * starts a drag, mouse-down on a row does not, the rectangle's
 * coordinates feed ``hitTest`` correctly, and ESC cancels by calling
 * ``onCancel`` without re-firing ``onSelect``.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick, effectScope } from 'vue'
import { useRectLasso } from '@/composables/useRectLasso'

function makeContainer({ width = 400, height = 300, scrollTop = 0, scrollLeft = 0 } = {}) {
  // Minimal DOM stub: getBoundingClientRect + scrollTop/Left + the
  // event-target API. JSDOM has all of this except getBoundingClientRect.
  const el = document.createElement('div')
  el.getBoundingClientRect = () => ({
    left: 0,
    top: 0,
    right: width,
    bottom: height,
    width,
    height,
    x: 0,
    y: 0,
    toJSON() {},
  })
  Object.defineProperty(el, 'scrollTop', {
    get: () => scrollTop,
    set: v => {
      scrollTop = v
    },
    configurable: true,
  })
  Object.defineProperty(el, 'scrollLeft', {
    get: () => scrollLeft,
    set: v => {
      scrollLeft = v
    },
    configurable: true,
  })
  document.body.appendChild(el)
  return el
}

function dispatch(el, type, props = {}) {
  // MouseEvent in JSDOM doesn't honour clientX/Y unless we set them
  // manually, so we extend the instance after construction.
  const ev = new MouseEvent(type, { bubbles: true, cancelable: true, button: 0, ...props })
  Object.defineProperty(ev, 'clientX', { value: props.clientX ?? 0 })
  Object.defineProperty(ev, 'clientY', { value: props.clientY ?? 0 })
  if (props.target) Object.defineProperty(ev, 'target', { value: props.target })
  el.dispatchEvent(ev)
  return ev
}

describe('useRectLasso', () => {
  let scope
  beforeEach(() => {
    scope = effectScope()
    document.body.innerHTML = ''
  })

  it('initialises in non-dragging state with hidden style', () => {
    const container = ref(makeContainer())
    let api
    scope.run(() => {
      api = useRectLasso({
        container,
        hitTest: () => [],
        onSelect: () => {},
      })
    })
    expect(api.isDragging.value).toBe(false)
    expect(api.rectStyle.value).toEqual({ display: 'none' })
    scope.stop()
  })

  it('starts a drag on mousedown over the container and emits hits on move', async () => {
    const el = makeContainer()
    const container = ref(el)
    const onSelect = vi.fn()
    const hitTest = vi.fn(rect => {
      const ids = []
      // Rows: 0..9, height 36px. Pick by floor.
      for (let i = Math.floor(rect.y1 / 36); i <= Math.floor(rect.y2 / 36); i++) {
        if (i >= 0 && i <= 9) ids.push(i)
      }
      return ids
    })

    let api
    scope.run(() => {
      api = useRectLasso({ container, hitTest, onSelect })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 50, clientY: 10, target: el })
    expect(api.isDragging.value).toBe(true)

    dispatch(el, 'mousemove', { clientX: 60, clientY: 80 })
    expect(hitTest).toHaveBeenCalled()
    expect(onSelect).toHaveBeenLastCalledWith([0, 1, 2])

    dispatch(el, 'mouseup', { clientX: 60, clientY: 80 })
    expect(api.isDragging.value).toBe(false)
    scope.stop()
  })

  it('does not start a drag when mousedown originates on an excluded element', async () => {
    const el = makeContainer()
    const container = ref(el)
    const row = document.createElement('div')
    row.className = 'mm-file-row'
    el.appendChild(row)

    const onSelect = vi.fn()
    let api
    scope.run(() => {
      api = useRectLasso({
        container,
        excludeSelector: '.mm-file-row, button',
        hitTest: () => [42],
        onSelect,
      })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 5, clientY: 5, target: row })
    expect(api.isDragging.value).toBe(false)

    dispatch(el, 'mousemove', { clientX: 50, clientY: 50 })
    expect(onSelect).not.toHaveBeenCalled()
    scope.stop()
  })

  it('cancels via Escape and calls onCancel without re-firing onSelect', async () => {
    const el = makeContainer()
    const container = ref(el)
    const onSelect = vi.fn()
    const onCancel = vi.fn()
    let api
    scope.run(() => {
      api = useRectLasso({
        container,
        hitTest: () => [1, 2, 3],
        onSelect,
        onCancel,
      })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 10, clientY: 10, target: el })
    dispatch(el, 'mousemove', { clientX: 100, clientY: 100 })
    expect(onSelect).toHaveBeenCalled()
    onSelect.mockClear()

    const escEvt = new KeyboardEvent('keydown', { key: 'Escape' })
    document.dispatchEvent(escEvt)

    expect(api.isDragging.value).toBe(false)
    expect(onCancel).toHaveBeenCalledTimes(1)
    // Pressing ESC must not fire onSelect again.
    expect(onSelect).not.toHaveBeenCalled()
    scope.stop()
  })

  it('clamps the rectangle to the container bounds when the drag overshoots', async () => {
    const el = makeContainer({ width: 200, height: 100 })
    const container = ref(el)
    let lastRect = null
    let _api
    scope.run(() => {
      _api = useRectLasso({
        container,
        hitTest: rect => {
          lastRect = rect
          return []
        },
        onSelect: () => {},
      })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 0, clientY: 0, target: el })
    dispatch(el, 'mousemove', { clientX: 9999, clientY: 9999 })

    expect(lastRect).not.toBeNull()
    expect(lastRect.x2).toBeLessThanOrEqual(200)
    expect(lastRect.y2).toBeLessThanOrEqual(100)
    scope.stop()
  })

  it('produces a positive-size rectStyle while dragging', async () => {
    const el = makeContainer()
    const container = ref(el)
    let api
    scope.run(() => {
      api = useRectLasso({ container, hitTest: () => [], onSelect: () => {} })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 30, clientY: 20, target: el })
    dispatch(el, 'mousemove', { clientX: 80, clientY: 70 })

    expect(api.rectStyle.value).toMatchObject({
      left: '30px',
      top: '20px',
      width: '50px',
      height: '50px',
    })
    scope.stop()
  })

  it('scales lasso coordinates by the admin zoom (pins the /z direction)', async () => {
    // clientX/Y are unzoomed; the rectangle/hit-test work in the zoomed
    // container space, so each coord maps through /0.5.
    Object.defineProperty(document.documentElement, 'currentCSSZoom', { value: 0.5, configurable: true })
    const el = makeContainer()
    const container = ref(el)
    let api
    scope.run(() => {
      api = useRectLasso({ container, hitTest: () => [], onSelect: () => {} })
    })
    await nextTick()

    dispatch(el, 'mousedown', { clientX: 30, clientY: 20, target: el })
    dispatch(el, 'mousemove', { clientX: 80, clientY: 70 })

    expect(api.rectStyle.value).toMatchObject({
      left: '60px',
      top: '40px',
      width: '100px',
      height: '100px',
    })
    delete document.documentElement.currentCSSZoom
    scope.stop()
  })
})
