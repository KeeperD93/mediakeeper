import { EPISODE_STATUS } from '@/constants/watchlist'

function downloadFile(content, filename, mime) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function useWlsExport(displayedSeries, ignoredSet) {
  function buildExportData() {
    const rows = []
    for (const s of displayedSeries.value) {
      for (const sn of s.seasons || []) {
        for (const ep of sn.episodes) {
          if (ep.status !== EPISODE_STATUS.MISSING) continue
          if (ignoredSet.value.has(`${s.tmdb_id}_s${sn.season}_e${ep.episode}`)) continue
          rows.push({
            serie: s.name,
            tmdb_id: s.tmdb_id,
            annee: s.year || '',
            saison: sn.season,
            episode: ep.episode,
            nom_episode: ep.name || '',
            date_diffusion: ep.air_date || '',
          })
        }
      }
    }
    return rows
  }

  function exportCSV() {
    const rows = buildExportData()
    if (!rows.length) return
    const headers = Object.keys(rows[0])
    const lines = [headers.join(';')]
    for (const r of rows)
      lines.push(headers.map(h => `"${String(r[h]).replace(/"/g, '""')}"`).join(';'))
    downloadFile(
      '﻿' + lines.join('\n'),
      `watchlist_manquants_${new Date().toISOString().slice(0, 10)}.csv`,
      'text/csv;charset=utf-8',
    )
  }

  function exportJSON() {
    const rows = buildExportData()
    if (!rows.length) return
    downloadFile(
      JSON.stringify(rows, null, 2),
      `watchlist_manquants_${new Date().toISOString().slice(0, 10)}.json`,
      'application/json',
    )
  }

  return { exportCSV, exportJSON }
}
