import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { useDashboardKeyboardMove } from '@/composables/useDashboardKeyboardMove'

const COL_NUM = 36

function buildLayout() {
  return [
    { i: 'A', x: 5, y: 3, w: 4, h: 5 },
    { i: 'B', x: 12, y: 0, w: 6, h: 5 },
  ]
}

function buildHarness({ editing = true } = {}) {
  const layout = ref(buildLayout())
  const editingRef = ref(editing)
  const onLayoutUpdated = vi.fn()
  const t = vi.fn((key, params) => (params ? `${key}:${JSON.stringify(params)}` : key))
  const api = useDashboardKeyboardMove({
    layout,
    editing: editingRef,
    colNum: COL_NUM,
    onLayoutUpdated,
    t,
  })
  return { layout, editingRef, onLayoutUpdated, t, api }
}

function key(name) {
  return { key: name, preventDefault: vi.fn() }
}

describe('useDashboardKeyboardMove', () => {
  it('a) editing=false: handleKeydown ignores everything', () => {
    const { api, layout } = buildHarness({ editing: false })
    const ev = key(' ')
    api.handleKeydown(ev, 'A')
    expect(api.movingItemId.value).toBe(null)
    expect(api.liveAnnouncement.value).toBe('')
    expect(ev.preventDefault).not.toHaveBeenCalled()
    expect(layout.value[0]).toEqual({ i: 'A', x: 5, y: 3, w: 4, h: 5 })
  })

  it('b) Space on item A enters move mode and announces movingWidget', () => {
    const { api } = buildHarness()
    const ev = key(' ')
    api.handleKeydown(ev, 'A')
    expect(api.movingItemId.value).toBe('A')
    expect(api.liveAnnouncement.value).toContain('movingWidget')
    expect(ev.preventDefault).toHaveBeenCalledOnce()
  })

  it('Enter behaves like Space for entering move mode', () => {
    const { api } = buildHarness()
    api.handleKeydown(key('Enter'), 'A')
    expect(api.movingItemId.value).toBe('A')
  })

  it('c) ArrowRight increments x by 1 and clamps to colNum - w', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    api.handleKeydown(key('ArrowRight'), 'A')
    expect(layout.value[0].x).toBe(6)
    expect(api.liveAnnouncement.value).toContain('movedTo')
    expect(api.liveAnnouncement.value).toContain('"x":6')

    layout.value[0].x = COL_NUM - layout.value[0].w
    api.handleKeydown(key('ArrowRight'), 'A')
    expect(layout.value[0].x).toBe(COL_NUM - layout.value[0].w)
  })

  it('d) ArrowLeft at x=0 stays at 0', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    layout.value[0].x = 0
    api.handleKeydown(key('ArrowLeft'), 'A')
    expect(layout.value[0].x).toBe(0)
  })

  it('ArrowUp at y=0 stays at 0; ArrowDown has no upper bound', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    layout.value[0].y = 0
    api.handleKeydown(key('ArrowUp'), 'A')
    expect(layout.value[0].y).toBe(0)
    for (let i = 0; i < 10; i++) api.handleKeydown(key('ArrowDown'), 'A')
    expect(layout.value[0].y).toBe(10)
  })

  it('e) Escape restores origin and clears movingItemId', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    api.handleKeydown(key('ArrowRight'), 'A')
    api.handleKeydown(key('ArrowDown'), 'A')
    expect(layout.value[0].x).toBe(6)
    expect(layout.value[0].y).toBe(4)
    const ev = key('Escape')
    api.handleKeydown(ev, 'A')
    expect(layout.value[0].x).toBe(5)
    expect(layout.value[0].y).toBe(3)
    expect(api.movingItemId.value).toBe(null)
    expect(api.liveAnnouncement.value).toContain('moveCancelled')
    expect(ev.preventDefault).toHaveBeenCalledOnce()
  })

  it('f) Space confirms, clears movingItemId and calls onLayoutUpdated', () => {
    const { api, layout, onLayoutUpdated } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    api.handleKeydown(key('ArrowRight'), 'A')
    api.handleKeydown(key(' '), 'A')
    expect(api.movingItemId.value).toBe(null)
    expect(api.liveAnnouncement.value).toContain('moveConfirmed')
    expect(onLayoutUpdated).toHaveBeenCalledOnce()
    expect(onLayoutUpdated).toHaveBeenCalledWith(layout.value)
  })

  it('Space on a different item while A is moving is ignored (no collision)', () => {
    const { api } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    expect(api.movingItemId.value).toBe('A')
    const ev = key(' ')
    api.handleKeydown(ev, 'B')
    expect(api.movingItemId.value).toBe('A')
    expect(ev.preventDefault).not.toHaveBeenCalled()
  })

  it('Arrow keys on a non-moving item are ignored', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    const before = { ...layout.value[1] }
    api.handleKeydown(key('ArrowRight'), 'B')
    expect(layout.value[1]).toEqual(before)
  })

  it('Other keys (Tab, letters) are ignored even in move mode', () => {
    const { api, layout } = buildHarness()
    api.handleKeydown(key(' '), 'A')
    const before = { ...layout.value[0] }
    const ev = key('Tab')
    api.handleKeydown(ev, 'A')
    expect(layout.value[0]).toEqual(before)
    expect(ev.preventDefault).not.toHaveBeenCalled()
  })
})
