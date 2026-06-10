import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

// Pointer-drag column resizing for a <table> with one <col> per column.
// `init(containerPx)` lays the columns out to fill the container exactly (so the
// table never overflows — a right-edge "wall"), seeding from the user's saved
// widths when `persistKey` is set, else from `defaults`. Resizing is zero-sum
// against the next column, so the total stays constant and the last column can
// never be pushed off-screen. `fixed` leading columns keep their default px and
// get no handle. `startResize(i, e)` wires the per-column drag handles (every
// column except the last one, which has no column to its right to trade with).
export function useColumnResize(defaults, { min = 56, fixed = 0, persistKey = '' } = {}) {
  const { apiGet, apiPut } = useApi()
  const base = [...defaults]
  const widths = ref([...defaults])
  const ready = ref(false)
  const total = computed(() => widths.value.reduce((a, b) => a + b, 0))
  let drag = null
  let saveTimer = null

  function distribute(ratios, containerPx) {
    const fixedSum = base.slice(0, fixed).reduce((a, b) => a + b, 0)
    const flexSum = ratios.slice(fixed).reduce((a, b) => a + b, 0) || 1
    const avail = Math.max(0, containerPx - fixedSum)
    const next = ratios.map((r, i) =>
      i < fixed ? base[i] : Math.max(min, Math.round((avail * r) / flexSum)),
    )
    const last = next.length - 1
    next[last] = Math.max(min, next[last] + (containerPx - next.reduce((a, b) => a + b, 0)))
    widths.value = next
    ready.value = true
  }

  async function init(containerPx) {
    if (!containerPx) return
    let ratios = base
    if (persistKey) {
      try {
        const map = await apiGet('/api/auth/table-columns')
        const saved = map && map[persistKey]
        if (Array.isArray(saved) && saved.length === base.length) ratios = saved.map(Number)
      } catch {
        /* ignore — fall back to defaults */
      }
    }
    distribute(ratios, containerPx)
  }

  function save() {
    if (!persistKey) return
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      apiPut('/api/auth/table-columns', { table: persistKey, widths: widths.value }).catch(() => {})
    }, 500)
  }

  function onMove(e) {
    if (!drag) return
    let d = e.clientX - drag.x
    d = Math.max(d, min - drag.w) // left column stays >= min
    d = Math.min(d, drag.wNext - min) // right column stays >= min
    widths.value[drag.i] = drag.w + d
    widths.value[drag.i + 1] = drag.wNext - d
  }
  function onUp() {
    const was = !!drag
    drag = null
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    if (was) save()
  }
  function startResize(i, e) {
    drag = { i, x: e.clientX, w: widths.value[i], wNext: widths.value[i + 1] }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    e.preventDefault()
    e.stopPropagation()
  }

  return { widths, total, ready, init, startResize }
}
