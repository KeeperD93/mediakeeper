import { ref, computed } from 'vue'

export function useTimelineNav(timelineItems) {
  const NOW = new Date().toISOString().slice(0, 10)
  const FROM = (() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 6)
    return d.toISOString().slice(0, 10)
  })()
  const TO = (() => {
    const d = new Date()
    d.setMonth(d.getMonth() + 6)
    return d.toISOString().slice(0, 10)
  })()

  const scrollRef = ref(null)
  let scrolled = false

  const entries = computed(() => {
    const m = {}
    for (const it of timelineItems.value) {
      if (it.date < FROM || it.date > TO) continue
      ;(m[it.date] || (m[it.date] = [])).push(it)
    }
    if (!m[NOW]) m[NOW] = []
    return Object.keys(m)
      .sort()
      .map(d => {
        const dt = new Date(d + 'T00:00:00')
        return {
          date: d,
          today: d === NOW,
          past: d < NOW,
          label: dt.toLocaleDateString(undefined, {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          }),
          items: m[d],
        }
      })
  })

  const months = computed(() => {
    const o = [],
      n = new Date()
    for (let i = -6; i <= 6; i++) {
      const d = new Date(n.getFullYear(), n.getMonth() + i, 1)
      const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      const s = d.toLocaleDateString(undefined, { month: 'short' }).replace('.', '').toUpperCase()
      const y = String(d.getFullYear()).slice(2)
      let first = k + '-01'
      for (const e of entries.value) {
        if (e.date.startsWith(k)) {
          first = e.date
          break
        }
      }
      o.push({ k, s, y, first, now: NOW.startsWith(k) })
    }
    return o
  })

  function goToday() {
    const c = scrollRef.value
    if (!c) return
    let t = c.querySelector(`[data-date="${NOW}"]`)
    if (!t) {
      let best = null,
        bd = Infinity
      c.querySelectorAll('[data-date]').forEach(r => {
        const d = Math.abs(new Date(r.dataset.date) - new Date(NOW))
        if (d < bd) {
          bd = d
          best = r
        }
      })
      t = best
    }
    if (t)
      c.scrollTo({
        top: Math.max(0, t.offsetTop - c.clientHeight / 3),
        behavior: scrolled ? 'smooth' : 'auto',
      })
  }

  function goMonth(d) {
    const c = scrollRef.value
    if (!c) return
    const rows = Array.from(c.querySelectorAll('[data-date]'))
    const t = rows.find(r => r.dataset.date >= d) || rows[rows.length - 1]
    if (t) c.scrollTo({ top: Math.max(0, t.offsetTop - 70), behavior: 'smooth' })
  }

  function doAutoScroll(rootRef) {
    if (scrolled) return
    const el = rootRef?.value
    if (!el || el.offsetParent === null) return
    const r = el.getBoundingClientRect()
    if (!r.height || !r.width) return
    goToday()
    scrolled = true
  }

  return { NOW, scrollRef, entries, months, goToday, goMonth, doAutoScroll }
}
