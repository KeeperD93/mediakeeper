<template>
  <div>
    <div class="wls-kpis">
      <div class="wls-kpi glass-kpi">
        <span class="wls-kpi-val wls-kpi-val-missing">{{ missingCount }}</span>
        <span class="wls-kpi-label">{{ $t('watchlist.missingEpisodes') }}</span>
        <span class="wls-kpi-sub">{{ $t('watchlist.outOfSeries', { count: filteredSeries.length }) }}</span>
      </div>
      <div class="wls-kpi glass-kpi">
        <span class="wls-kpi-val wls-kpi-val-upcoming">{{ upcomingCount }}</span>
        <span class="wls-kpi-label">{{ $t('watchlist.upcoming') }}</span>
        <span class="wls-kpi-sub">{{ $t('watchlist.upcomingEpisodes') }}</span>
      </div>
      <div class="wls-kpi glass-kpi">
        <span class="wls-kpi-val wls-kpi-val-tracked">{{ tracked.length }}</span>
        <span class="wls-kpi-label">{{ $t('watchlist.trackedContent') }}</span>
        <span class="wls-kpi-sub">{{ $t('watchlist.active') }}</span>
      </div>
      <div class="wls-kpi glass-kpi">
        <span class="wls-kpi-val wls-kpi-val-ignored">{{ ignoredCount }}</span>
        <span class="wls-kpi-label">{{ $t('watchlist.ignoredEpisodes') }}</span>
        <span class="wls-kpi-sub">{{ $t('watchlist.hidden') }}</span>
      </div>
    </div>

    <!-- Barre outils : recherche + tri + groupement + export -->
    <div class="wls-toolbar">
      <div class="wls-search-wrap">
        <Search class="wls-search-icon" :size="14" />
        <input v-model="searchQuery" class="wls-search" type="text" :placeholder="$t('watchlist.searchSeries')" />
        <button v-if="searchQuery" class="wls-search-clear" @click="searchQuery=''"><X :size="12" /></button>
      </div>

      <div class="wls-filters">
        <select v-model="sortBy" class="wls-select">
          <option value="missing">{{ $t('watchlist.sortMissing') }}</option>
          <option value="name">{{ $t('watchlist.sortName') }}</option>
          <option value="progress">{{ $t('watchlist.sortCompletion') }}</option>
          <option value="year">{{ $t('watchlist.sortYear') }}</option>
        </select>

        <select v-model="groupBy" class="wls-select">
          <option value="none">{{ $t('watchlist.groupNone') }}</option>
          <option value="status">{{ $t('watchlist.groupStatus') }}</option>
          <option value="year">{{ $t('watchlist.groupYear') }}</option>
        </select>

        <div class="wls-export-group">
          <button class="wls-export-btn" :title="$t('watchlist.exportCsv')" @click="exportCSV">
            <Download :size="15" />
            CSV
          </button>
          <button class="wls-export-btn" :title="$t('watchlist.exportJson')" @click="exportJSON">
            <Download :size="15" />
            JSON
          </button>
        </div>
      </div>
    </div>

    <div class="wls-header">
      <p class="wls-count">{{ displayedSeries.length }} {{ $t('common.series', displayedSeries.length).toLowerCase() }}</p>
      <button class="wls-scan-btn" :disabled="loading" @click="$emit('scan')">
        <span v-if="loading" class="mk-spin wls-scan-spin" />
        <RefreshCw v-else :size="13" />
        {{ $t('common.scan') }}
      </button>
    </div>

    <div v-if="!displayedSeries.length" class="wls-empty">
      <CircleCheck :size="48" :stroke-width="1.5" class="wls-empty-icon" />
      <p>{{ searchQuery ? $t('common.noResultsFor', { query: searchQuery }) : $t('watchlist.noMissing') }}</p>
    </div>

    <!-- Grouped or not -->
    <template v-if="groupBy !== 'none' && displayedSeries.length">
      <div v-for="g in groupedSeries" :key="g.label" class="wls-group">
        <div class="wls-group-label">{{ g.label }} <span class="wls-group-count">{{ g.items.length }}</span></div>
        <div class="wls-grid">
          <WlSeriesCard
            v-for="s in g.items" :key="s.tmdb_id"
            :series="s" :ignored-set="ignoredSet"
            @ignore-ep="(tid,season,ep) => ignoreEpisode(`${tid}_s${season}_e${ep}`)"
            @ignore-season="keys => ignoreMultiple(keys)"
          />
        </div>
      </div>
    </template>

    <div v-else-if="displayedSeries.length" class="wls-grid">
      <WlSeriesCard
        v-for="s in displayedSeries" :key="s.tmdb_id"
        :series="s" :ignored-set="ignoredSet"
        @ignore-ep="(tid,season,ep) => ignoreEpisode(`${tid}_s${season}_e${ep}`)"
        @ignore-season="keys => ignoreMultiple(keys)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWatchlist } from '@/composables/useWatchlist'
import WlSeriesCard from './WlSeriesCard.vue'
import { CircleCheck, Download, RefreshCw, Search, X } from 'lucide-vue-next'
import { EPISODE_STATUS, SERIES_STATUS } from '@/constants/watchlist'

const { t } = useI18n()
defineProps({ type: String })
defineEmits(['scan'])

const { data, loading, ignoredSet, ignored, tracked, missingCount, upcomingCount, ignoreEpisode, ignoreMultiple } = useWatchlist()
const ignoredCount = computed(() => ignored.value.length)

const searchQuery = ref('')
const sortBy = ref('missing')
const groupBy = ref('none')

const filteredSeries = computed(() => {
  if (!data.value?.series) return []
  const ign = ignoredSet.value
  return data.value.series
    .map(s => {
      const mc = (s.seasons||[]).reduce((a,sn) =>
        a + sn.episodes.filter(e => e.status===EPISODE_STATUS.MISSING && !ign.has(`${s.tmdb_id}_s${sn.season}_e${e.episode}`)).length, 0)
      const total = (s.seasons||[]).reduce((a,sn) => a + sn.episode_count_tmdb, 0)
      const present = (s.seasons||[]).reduce((a,sn) => a + sn.episode_count_emby, 0)
      const pct = total ? Math.round((present/total)*100) : 0
      return { ...s, _fm: mc, _pct: pct }
    })
    .filter(s => s._fm > 0)
})

const displayedSeries = computed(() => {
  let list = [...filteredSeries.value]

  // Recherche
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(s => s.name.toLowerCase().includes(q))
  }

  // Tri
  if (sortBy.value === 'missing') list.sort((a,b) => b._fm - a._fm)
  else if (sortBy.value === 'name') list.sort((a,b) => a.name.localeCompare(b.name))
  else if (sortBy.value === 'progress') list.sort((a,b) => a._pct - b._pct)
  else if (sortBy.value === 'year') list.sort((a,b) => (b.year||0) - (a.year||0))

  return list
})

const groupedSeries = computed(() => {
  if (groupBy.value === 'none') return []
  const map = {}
  for (const s of displayedSeries.value) {
    let key
    if (groupBy.value === 'status') {
      key = s.status === SERIES_STATUS.ENDED || s.status === SERIES_STATUS.CANCELED ? 'Ended / Canceled' : 'Ongoing'
    } else if (groupBy.value === 'year') {
      key = s.year ? String(s.year) : 'Unknown'
    } else {
      key = 'Other'
    }
    if (!map[key]) map[key] = { label: key, items: [] }
    map[key].items.push(s)
  }
  const groups = Object.values(map)
  if (groupBy.value === 'year') groups.sort((a,b) => b.label.localeCompare(a.label))
  else groups.sort((a,b) => a.label.localeCompare(b.label))
  return groups
})

// --- Export ---
function buildExportData() {
  const rows = []
  for (const s of displayedSeries.value) {
    for (const sn of (s.seasons||[])) {
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

function downloadFile(content, filename, mime) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function exportCSV() {
  const rows = buildExportData()
  if (!rows.length) return
  const headers = Object.keys(rows[0])
  const lines = [headers.join(';')]
  for (const r of rows) lines.push(headers.map(h => `"${String(r[h]).replace(/"/g,'""')}"`).join(';'))
  downloadFile('\ufeff' + lines.join('\n'), `watchlist_manquants_${new Date().toISOString().slice(0,10)}.csv`, 'text/csv;charset=utf-8')
}

function exportJSON() {
  const rows = buildExportData()
  if (!rows.length) return
  downloadFile(JSON.stringify(rows, null, 2), `watchlist_manquants_${new Date().toISOString().slice(0,10)}.json`, 'application/json')
}
</script>

<style scoped>
.wls-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px; }
.glass-kpi { background:var(--surface-1); backdrop-filter:var(--blur-sm); border:.5px solid var(--border-default); border-radius:var(--radius-card); padding:14px 16px; display:flex; flex-direction:column; gap:3px; transition:border-color var(--duration-base); }
.glass-kpi:hover { border-color:rgba(99,102,241,.2); }
.wls-kpi-val { font-size:1.5rem; font-weight:var(--font-bold); font-family:'SF Mono','Cascadia Mono',monospace; line-height:var(--lh-tight); }
.wls-kpi-val-missing { color:var(--color-error); }
.wls-kpi-val-upcoming { color:var(--color-info); }
.wls-kpi-val-tracked { color:#a78bfa; }
.wls-kpi-val-ignored { color:var(--color-warning); }
.wls-kpi-label { font-size:var(--text-2xs); color:var(--text-muted); text-transform:uppercase; letter-spacing:.5px; }
.wls-kpi-sub { font-size:var(--text-2xs); color:var(--text-secondary); }

/* Toolbar */
.wls-toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:14px; }
.wls-search-wrap { position:relative; flex:1; min-width:180px; }
.wls-search-icon { position:absolute; left:10px; top:50%; transform:translateY(-50%); color:var(--text-muted); pointer-events:none; }
.wls-search { width:100%; padding:7px 30px 7px 32px; border-radius:var(--radius-btn); border:.5px solid var(--border-strong); background:rgba(255,255,255,.03); color:var(--text-primary); font-size:var(--text-sm); font-family:inherit; outline:none; transition:border-color var(--duration-fast); }
.wls-search:focus { border-color:rgba(99,102,241,.4); }
.wls-search::placeholder { color:var(--text-muted); }
.wls-search-clear { position:absolute; right:8px; top:50%; transform:translateY(-50%); background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:var(--text-2xs); padding:2px 4px; }
.wls-filters { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.wls-select { padding:6px 10px; border-radius:var(--radius-btn); border:.5px solid var(--border-strong); background:rgba(255,255,255,.03); color:var(--text-secondary); font-size:var(--text-2xs); font-family:inherit; cursor:pointer; outline:none; }
.wls-select:focus { border-color:rgba(99,102,241,.4); }
.wls-export-group { display:flex; gap:4px; }
.wls-export-btn { display:inline-flex; align-items:center; gap:6px; padding:7px 14px; border-radius:var(--radius-btn); border:.5px solid var(--border-strong); background:rgba(255,255,255,.03); color:var(--text-muted); font-size:var(--text-sm); font-weight:var(--font-medium); font-family:inherit; cursor:pointer; transition:all var(--duration-fast); }
.wls-export-btn:hover { background:rgba(99,102,241,.1); color:var(--accent-400); border-color:rgba(99,102,241,.25); }

/* Group */
.wls-group { margin-bottom:20px; }
.wls-group-label { font-size:var(--text-2xs); font-weight:var(--font-bold); text-transform:uppercase; letter-spacing:.5px; color:var(--accent-400); padding:6px 0; border-bottom:.5px solid var(--border-default); margin-bottom:8px; display:flex; align-items:center; gap:8px; }
.wls-group-count { font-size:var(--text-3xs); font-weight:var(--font-bold); padding:1px 7px; border-radius:var(--radius-sm); background:rgba(99,102,241,.12); color:var(--accent-400); }

.wls-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.wls-count { font-size:var(--text-sm); color:var(--text-muted); }
.wls-scan-btn { display:inline-flex; align-items:center; gap:5px; padding:6px 14px; border-radius:var(--radius-btn); font-size:var(--text-sm); font-weight:var(--font-medium); background:rgba(var(--accent-rgb),.1); color:var(--accent-400); border:.5px solid rgba(var(--accent-rgb),.25); cursor:pointer; transition:all var(--duration-fast); font-family:inherit; }
.wls-scan-btn:hover { background:var(--accent-600); color:#fff; border-color:transparent; }
.wls-scan-btn:disabled { opacity:.5; cursor:not-allowed; }
.wls-empty { display:flex; flex-direction:column; align-items:center; gap:12px; padding:64px 24px; color:var(--text-muted); font-size:var(--text-base); }
.wls-empty-icon { opacity:.2; color:var(--text-muted); }
.wls-scan-spin { width:13px; height:13px; }
.wls-grid { columns:2; column-gap:8px; }
.wls-grid > * { break-inside:avoid; margin-bottom:8px; }
@media(max-width:1024px) { .wls-grid{columns:1} .wls-kpis{grid-template-columns:repeat(2,1fr)} .wls-toolbar{flex-direction:column} .wls-search-wrap{min-width:100%} }
</style>
