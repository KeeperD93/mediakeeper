export function sortArrow(col, currentCol, order) {
  if (currentCol !== col) return '↕'
  return order === 'desc' ? '▼' : '▲'
}

export function sortArrowClass(col, currentCol) {
  return currentCol === col
    ? 'stats-sort-arrow stats-sort-arrow--active'
    : 'stats-sort-arrow stats-sort-arrow--idle'
}

export function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

export function fluxBadgeClass(m) {
  return m === 'DirectPlay' ? 'flux-direct' : m === 'Transcode' ? 'flux-transcode' : 'flux-other'
}

// Real percentage of the media watched (position reached / total runtime),
// clamped to 0-100. Returns null when the total runtime is unknown
// (legacy/imported rows) so the UI hides the bar.
export function watchedPct(positionTicks, runtimeTicks) {
  if (!runtimeTicks || runtimeTicks <= 0) return null
  const pct = Math.round((positionTicks / runtimeTicks) * 100)
  return Math.max(0, Math.min(100, pct))
}
