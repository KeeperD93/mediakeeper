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
