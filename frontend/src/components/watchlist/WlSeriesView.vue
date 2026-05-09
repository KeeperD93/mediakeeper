<template>
  <div>
    <WlsKpis
      :missing-count="missingCount"
      :upcoming-count="upcomingCount"
      :tracked-count="tracked.length"
      :ignored-count="ignoredCount"
      :filtered-series-count="filteredSeries.length"
    />

    <WlsToolbar
      v-model:search-query="searchQuery"
      v-model:sort-by="sortBy"
      v-model:group-by="groupBy"
      @export-csv="exportCSV"
      @export-json="exportJSON"
    />

    <div class="wls-header">
      <p class="wls-count">
        {{ displayedSeries.length }} {{ $t('common.series', displayedSeries.length).toLowerCase() }}
      </p>
      <button class="wls-scan-btn" :disabled="loading" @click="$emit('scan')">
        <span v-if="loading" class="mk-spin wls-scan-spin" />
        <RefreshCw v-else :size="13" />
        {{ $t('common.scan') }}
      </button>
    </div>

    <div v-if="!displayedSeries.length" class="wls-empty">
      <CircleCheck :size="48" :stroke-width="1.5" class="wls-empty-icon" />
      <p>
        {{
          searchQuery
            ? $t('common.noResultsFor', { query: searchQuery })
            : $t('watchlist.noMissing')
        }}
      </p>
    </div>

    <!-- Grouped or not -->
    <template v-if="groupBy !== 'none' && displayedSeries.length">
      <div v-for="g in groupedSeries" :key="g.label" class="wls-group">
        <div class="wls-group-label">
          {{ g.label }}
          <span class="wls-group-count">{{ g.items.length }}</span>
        </div>
        <div class="wls-grid">
          <WlSeriesCard
            v-for="s in g.items"
            :key="s.tmdb_id"
            :series="s"
            :ignored-set="ignoredSet"
            @ignore-ep="(tid, season, ep) => ignoreEpisode(`${tid}_s${season}_e${ep}`)"
            @ignore-season="keys => ignoreMultiple(keys)"
          />
        </div>
      </div>
    </template>

    <div v-else-if="displayedSeries.length" class="wls-grid">
      <WlSeriesCard
        v-for="s in displayedSeries"
        :key="s.tmdb_id"
        :series="s"
        :ignored-set="ignoredSet"
        @ignore-ep="(tid, season, ep) => ignoreEpisode(`${tid}_s${season}_e${ep}`)"
        @ignore-season="keys => ignoreMultiple(keys)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import WlSeriesCard from './WlSeriesCard.vue'
import WlsKpis from './WlSeriesView/WlsKpis.vue'
import WlsToolbar from './WlSeriesView/WlsToolbar.vue'
import { useWlsExport } from './WlSeriesView/useWlsExport'
import { CircleCheck, RefreshCw } from 'lucide-vue-next'
import { EPISODE_STATUS, SERIES_STATUS } from '@/constants/watchlist'

defineProps({ type: String })
defineEmits(['scan'])

const {
  data,
  loading,
  ignoredSet,
  ignored,
  tracked,
  missingCount,
  upcomingCount,
  ignoreEpisode,
  ignoreMultiple,
} = useWatchlist()
const ignoredCount = computed(() => ignored.value.length)

const searchQuery = ref('')
const sortBy = ref('missing')
const groupBy = ref('none')

const filteredSeries = computed(() => {
  if (!data.value?.series) return []
  const ign = ignoredSet.value
  return data.value.series
    .map(s => {
      const mc = (s.seasons || []).reduce(
        (a, sn) =>
          a +
          sn.episodes.filter(
            e =>
              e.status === EPISODE_STATUS.MISSING &&
              !ign.has(`${s.tmdb_id}_s${sn.season}_e${e.episode}`),
          ).length,
        0,
      )
      const total = (s.seasons || []).reduce((a, sn) => a + sn.episode_count_tmdb, 0)
      const present = (s.seasons || []).reduce((a, sn) => a + sn.episode_count_emby, 0)
      const pct = total ? Math.round((present / total) * 100) : 0
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
  if (sortBy.value === 'missing') list.sort((a, b) => b._fm - a._fm)
  else if (sortBy.value === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
  else if (sortBy.value === 'progress') list.sort((a, b) => a._pct - b._pct)
  else if (sortBy.value === 'year') list.sort((a, b) => (b.year || 0) - (a.year || 0))

  return list
})

const groupedSeries = computed(() => {
  if (groupBy.value === 'none') return []
  const map = {}
  for (const s of displayedSeries.value) {
    let key
    if (groupBy.value === 'status') {
      key =
        s.status === SERIES_STATUS.ENDED || s.status === SERIES_STATUS.CANCELED
          ? 'Ended / Canceled'
          : 'Ongoing'
    } else if (groupBy.value === 'year') {
      key = s.year ? String(s.year) : 'Unknown'
    } else {
      key = 'Other'
    }
    if (!map[key]) map[key] = { label: key, items: [] }
    map[key].items.push(s)
  }
  const groups = Object.values(map)
  if (groupBy.value === 'year') groups.sort((a, b) => b.label.localeCompare(a.label))
  else groups.sort((a, b) => a.label.localeCompare(b.label))
  return groups
})

const { exportCSV, exportJSON } = useWlsExport(displayedSeries, ignoredSet)
</script>

<style scoped>
/* Group */
.wls-group {
  margin-bottom: 20px;
}
.wls-group-label {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--accent-400);
  padding: 6px 0;
  border-bottom: 0.5px solid var(--border-default);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.wls-group-count {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  padding: 1px 7px;
  border-radius: var(--radius-sm);
  background: rgb(99, 102, 241, 0.12);
  color: var(--accent-400);
}

.wls-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.wls-count {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.wls-scan-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
  border: 0.5px solid rgb(var(--accent-rgb), 0.25);
  cursor: pointer;
  transition: all var(--duration-fast);
  font-family: inherit;
}
.wls-scan-btn:hover {
  background: var(--accent-600);
  color: #fff;
  border-color: transparent;
}
.wls-scan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.wls-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 24px;
  color: var(--text-muted);
  font-size: var(--text-base);
}
.wls-empty-icon {
  opacity: 0.2;
  color: var(--text-muted);
}
.wls-scan-spin {
  width: 13px;
  height: 13px;
}
.wls-grid {
  columns: 2;
  column-gap: 8px;
}
.wls-grid > * {
  break-inside: avoid;
  margin-bottom: 8px;
}
@media (max-width: 1024px) {
  .wls-grid {
    columns: 1;
  }
}
</style>
