import { ref, computed } from 'vue'
import { rootZoom } from '@/utils/zoom'

export function useChartsHeatmap(dailyChart, locale) {
  function localeTag() {
    const l = locale.value || 'fr'
    return l === 'fr' ? 'fr-FR' : l === 'en' ? 'en-US' : l
  }

  const hmMonthGrid = computed(() => {
    if (!dailyChart.value?.data) return []
    const byDate = {}
    for (const [date, libs] of Object.entries(dailyChart.value.data)) {
      let total = 0
      if (typeof libs === 'object' && libs !== null)
        for (const lib of Object.values(libs))
          total += lib?.plays || lib?.count || (typeof lib === 'number' ? lib : 0)
      if (total > 0) byDate[date] = total
    }
    const now = new Date()
    now.setHours(0, 0, 0, 0)
    const rows = []
    for (let m = 11; m >= 0; m--) {
      const refDate = new Date(now.getFullYear(), now.getMonth() - m, 1)
      const year = refDate.getFullYear()
      const month = refDate.getMonth()
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      const lt = localeTag()
      const label = refDate.toLocaleDateString(lt, { month: 'short', year: '2-digit' })
      const days = []
      for (let d = 1; d <= 31; d++) {
        if (d > daysInMonth) {
          days.push({ count: 0, label: '', date: '' })
          continue
        }
        const dayDate = new Date(year, month, d)
        if (dayDate > now) {
          days.push({ count: 0, label: '', date: '' })
          continue
        }
        const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
        const lbl = dayDate.toLocaleDateString(lt, {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })
        days.push({ count: byDate[iso] || 0, label: lbl, date: iso })
      }
      rows.push({ label, days })
    }
    return rows
  })

  const hmGridMax = computed(() => {
    if (!hmMonthGrid.value.length) return 1
    return Math.max(1, ...hmMonthGrid.value.flatMap(r => r.days.map(d => d.count)))
  })

  function hmCellColor(count) {
    if (!count) return 'var(--heat-0, rgba(255,255,255,0.05))'
    const r = count / hmGridMax.value
    if (r <= 0.15) return 'var(--heat-1, rgba(99,102,241,0.2))'
    if (r <= 0.35) return 'var(--heat-2, rgba(99,102,241,0.4))'
    if (r <= 0.65) return 'var(--heat-3, rgba(99,102,241,0.65))'
    return 'var(--heat-4, rgba(99,102,241,0.9))'
  }

  const hmMonthPeak = computed(() => {
    let mx = 0,
      lbl = '—'
    for (const row of hmMonthGrid.value)
      for (const d of row.days)
        if (d.count > mx) {
          mx = d.count
          lbl = d.label
        }
    return { count: mx, label: lbl }
  })

  const hmTip = ref({ visible: false, x: 0, y: 0, label: '', count: 0 })
  function hmTooltipShow(e, cell) {
    if (!cell.date) return
    const z = rootZoom() // admin zoom: divide the final position (utils/zoom)
    const rect = e.target.getBoundingClientRect()
    hmTip.value = {
      visible: true,
      x: (rect.left + rect.width / 2) / z,
      y: (rect.top - 8) / z,
      label: cell.label,
      count: cell.count,
    }
  }
  function hmTooltipHide() {
    hmTip.value.visible = false
  }

  return { hmMonthGrid, hmCellColor, hmMonthPeak, hmTip, hmTooltipShow, hmTooltipHide }
}
