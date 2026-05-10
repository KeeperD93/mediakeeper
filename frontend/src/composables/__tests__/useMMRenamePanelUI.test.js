/**
 * Vitest coverage for the rename-panel lasso composable.
 *
 * The composable wires ``useRectLasso`` against the generated-names
 * list and exposes a higher-order ``deleteSelected`` so the panel can
 * inject ``removeRight`` from ``useMediaManager``. Tests cover the
 * lasso → selection plumbing and the descending-splice deletion
 * contract that keeps indices stable.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick, effectScope } from 'vue'
import { useMMRenamePanelUI } from '@/composables/useMMRenamePanelUI'

const lassoCallbacks = {}
vi.mock('@/composables/useRectLasso', () => ({
  useRectLasso: opts => {
    lassoCallbacks.onSelect = opts.onSelect
    lassoCallbacks.onCancel = opts.onCancel
    lassoCallbacks.hitTest = opts.hitTest
    return { isDragging: ref(false), rectStyle: ref({ display: 'none' }) }
  },
}))

function makeRightListRef() {
  const focus = vi.fn()
  const el = { focus, querySelectorAll: () => [] }
  return { ref: ref(el), focus }
}

describe('useMMRenamePanelUI', () => {
  let scope
  beforeEach(() => {
    scope = effectScope()
    Object.keys(lassoCallbacks).forEach(k => delete lassoCallbacks[k])
  })

  it('mounts with an empty selection', () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }, { name: 'b' }, { name: 'c' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    expect(api.selectedNew.value).toBeInstanceOf(Set)
    expect(api.selectedNew.value.size).toBe(0)
    scope.stop()
  })

  it('lasso onSelect populates selectedNew', () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }, { name: 'b' }, { name: 'c' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    lassoCallbacks.onSelect([0, 2])
    expect(api.selectedNew.value).toEqual(new Set([0, 2]))
    scope.stop()
  })

  it('deleteSelected splices descending and clears the selection', () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }, { name: 'b' }, { name: 'c' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    lassoCallbacks.onSelect([0, 2])
    const removeRight = vi.fn()
    api.deleteSelected(removeRight)
    // Descending order: index 2 first, then index 0, so the second
    // splice still targets the row that was originally at 0.
    expect(removeRight).toHaveBeenNthCalledWith(1, 2)
    expect(removeRight).toHaveBeenNthCalledWith(2, 0)
    expect(api.selectedNew.value.size).toBe(0)
    scope.stop()
  })

  it('clearSelection empties the selection', () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }, { name: 'b' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    lassoCallbacks.onSelect([1])
    expect(api.selectedNew.value.size).toBe(1)
    api.clearSelection()
    expect(api.selectedNew.value.size).toBe(0)
    scope.stop()
  })

  it('clears selection when the underlying list empties', async () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }, { name: 'b' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    lassoCallbacks.onSelect([0])
    expect(api.selectedNew.value.size).toBe(1)
    newNames.value = []
    await nextTick()
    expect(api.selectedNew.value.size).toBe(0)
    scope.stop()
  })

  it('deleteSelected is a no-op when the selection is empty or removeRight is missing', () => {
    const { ref: rightListRef } = makeRightListRef()
    const newNames = ref([{ name: 'a' }])
    let api
    scope.run(() => {
      api = useMMRenamePanelUI({ rightListRef, newNames })
    })
    const removeRight = vi.fn()
    api.deleteSelected(removeRight)
    expect(removeRight).not.toHaveBeenCalled()
    lassoCallbacks.onSelect([0])
    api.deleteSelected(undefined)
    expect(removeRight).not.toHaveBeenCalled()
    expect(api.selectedNew.value.size).toBe(1)
    scope.stop()
  })
})
