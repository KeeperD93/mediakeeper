import { afterEach, describe, it, expect, vi } from 'vitest'
import { effectScope } from 'vue'

// useColumnResize calls useApi() at construction; the resize maths under test
// never touches the network, so a no-op stub keeps it out of the way.
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: vi.fn(), apiPut: vi.fn() }),
}))

import { useColumnResize } from '@/composables/useColumnResize'

// Run inside an effect scope so onScopeDispose has somewhere to register and
// teardown removes the window drag listeners between tests.
function setup() {
  const scope = effectScope()
  // No persistKey → save() is a no-op (no debounced apiPut to leak).
  const api = scope.run(() => useColumnResize([100, 100, 100], { min: 56 }))
  return { ...api, scope }
}

function drag({ startResize }, col, fromX, toX) {
  startResize(col, { clientX: fromX, preventDefault() {}, stopPropagation() {} })
  window.dispatchEvent(new MouseEvent('pointermove', { clientX: toX }))
  window.dispatchEvent(new MouseEvent('pointerup'))
}

describe('useColumnResize.onMove', () => {
  afterEach(() => {
    delete document.documentElement.currentCSSZoom
  })

  it('is zero-sum against the next column on a normal drag', () => {
    const ctx = setup()
    drag(ctx, 0, 0, 20) // drag the boundary +20px
    expect(ctx.widths.value[0]).toBe(120)
    expect(ctx.widths.value[1]).toBe(80)
    expect(ctx.widths.value[0] + ctx.widths.value[1]).toBe(200) // sum constant
    ctx.scope.stop()
  })

  it('floors the right neighbour at min when dragging far right', () => {
    const ctx = setup()
    drag(ctx, 0, 0, 1000) // overshoot to the right
    expect(ctx.widths.value[1]).toBe(56) // right column clamped to min
    expect(ctx.widths.value[0]).toBe(144) // 200 - 56
    expect(ctx.widths.value[0] + ctx.widths.value[1]).toBe(200)
    ctx.scope.stop()
  })

  it('floors the dragged column at min when dragging far left', () => {
    const ctx = setup()
    drag(ctx, 0, 0, -1000) // overshoot to the left
    expect(ctx.widths.value[0]).toBe(56) // dragged column clamped to min
    expect(ctx.widths.value[1]).toBe(144)
    expect(ctx.widths.value[0] + ctx.widths.value[1]).toBe(200)
    ctx.scope.stop()
  })

  it('scales the drag delta by the admin zoom (pins the /z direction)', () => {
    // Pointer coords are unzoomed; the column widths live in the zoomed layout,
    // so a 20px unzoomed drag must move the boundary 20/0.5 = 40 layout px.
    Object.defineProperty(document.documentElement, 'currentCSSZoom', { value: 0.5, configurable: true })
    const ctx = setup()
    drag(ctx, 0, 0, 20)
    expect(ctx.widths.value[0]).toBe(140)
    expect(ctx.widths.value[1]).toBe(60)
    ctx.scope.stop()
  })
})
