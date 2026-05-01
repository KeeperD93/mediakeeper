<template>
  <div class="tab-panel">
    <div v-if="minimap24h.length" class="minimap-wrap glass-card">
      <div class="minimap-header"><span class="minimap-title">{{ $t('stats.last24h') }}</span><span class="minimap-count">{{ minimapStats.total }} {{ $t('stats.plays_unit') }}</span></div>
      <div class="minimap-hours">
        <div v-for="h in 24" :key="'mh24' + h" class="minimap-hour-col" :title="minimapHourData[h - 1].title">
          <div class="minimap-hour-fill" :style="{ height: minimapHourData[h - 1].pct + '%', background: minimapHourData[h - 1].color }" />
        </div>
      </div>
      <div class="minimap-hlabels">
        <span v-for="h in [0, 3, 6, 9, 12, 15, 18, 21]" :key="'ml' + h" class="minimap-hlabel">{{ h }}h</span>
      </div>
      <div class="minimap-legend">
        <span class="minimap-leg"><span class="minimap-ldot minimap-ldot-direct" />{{ $t('stats.directPlay') }}</span>
        <span class="minimap-leg"><span class="minimap-ldot minimap-ldot-transcode" />{{ $t('stats.transcodeLabel') }}</span>
        <span class="minimap-leg"><span class="minimap-ldot minimap-ldot-other" />{{ $t('stats.otherStream') }}</span>
      </div>
    </div>

    <div class="glass-card tbl-wrap tbl-wrap-activity">
      <div class="tbl-header">
        <h2 class="tbl-title">{{ $t('stats.activityHistory') }}</h2>
        <button v-if="activitySelected.size" class="act-bulk-del-btn" @click="bulkDeleteActivity">
          <Trash2 :size="13" />
          {{ $t('common.delete') }} ({{ activitySelected.size }})
        </button>
        <div class="tbl-controls">
          <div class="tbl-ctrl"><span class="ctrl-lbl">{{ $t('common.showPerPage') }}</span><select v-model="activityPerPage" class="ctrl-sel" @change="activityCursorHistory = []; fetchActivityData('')"><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option><option :value="200">200</option><option :value="500">500</option></select></div>
          <input v-model="activitySearch" class="ctrl-search" :placeholder="$t('common.search')" @input="debouncedFetchActivity" />
        </div>
      </div>
      <div v-if="loadingActivity && !activity.items.length" class="tbl-loading">
        <div v-for="n in 5" :key="n" class="skel-tbl-row"><div class="skel-line w40" /><div class="skel-line w60" /><div class="skel-line w30" /></div>
      </div>
      <div v-else class="tbl-scroll">
        <table class="dt">
          <colgroup><col class="col-w36"/><col class="col-w11p"/><col class="col-w26p"/><col class="col-w11p"/><col class="col-w13p"/><col class="col-w9p"/><col class="col-w11p"/><col class="col-w11p"/></colgroup>
          <thead>
            <tr>
              <th class="dt-c"><input type="checkbox" class="act-chk" :checked="activityAllChecked" @change="toggleActivitySelectAll" /></th>
              <th class="sortable" @click="toggleActivitySort('user')">{{ $t('common.user') }} <span :class="sortArrowClass('user', activitySortBy)">{{ sortArrow('user', activitySortBy, activitySortOrder) }}</span></th>
              <th class="sortable" @click="toggleActivitySort('title')">{{ $t('stats.title') }} <span :class="sortArrowClass('title', activitySortBy)">{{ sortArrow('title', activitySortBy, activitySortOrder) }}</span></th>
              <th class="sortable" @click="toggleActivitySort('client')">{{ $t('common.client') }} <span :class="sortArrowClass('client', activitySortBy)">{{ sortArrow('client', activitySortBy, activitySortOrder) }}</span></th>
              <th>{{ $t('common.device') }}</th>
              <th class="sortable dt-c" @click="toggleActivitySort('play_method')">{{ $t('stats.stream') }} <span :class="sortArrowClass('play_method', activitySortBy)">{{ sortArrow('play_method', activitySortBy, activitySortOrder) }}</span></th>
              <th class="sortable dt-r" @click="toggleActivitySort('duration')">{{ $t('common.durationLabel') }} <span :class="sortArrowClass('duration', activitySortBy)">{{ sortArrow('duration', activitySortBy, activitySortOrder) }}</span></th>
              <th class="sortable dt-r" @click="toggleActivitySort('started_at')">{{ $t('common.date') }} <span :class="sortArrowClass('started_at', activitySortBy)">{{ sortArrow('started_at', activitySortBy, activitySortOrder) }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!sortedActivity.length"><td colspan="8" class="dt-empty">{{ $t('stats.noData') }}</td></tr>
            <tr v-for="it in sortedActivity" :key="it.id" :class="{ 'act-row-selected': activitySelected.has(it.id) }">
              <td class="dt-c"><input type="checkbox" class="act-chk" :checked="activitySelected.has(it.id)" @change="toggleActivitySelect(it.id)" /></td>
              <td class="dt-name">{{ it.user }}</td>
              <td class="dt-sec">{{ it.title }}<span v-if="it.episode" class="dt-ep">{{ it.episode }}</span></td>
              <td class="dt-sec">{{ it.client || '—' }}</td>
              <td class="dt-sec">{{ it.device || '—' }}</td>
              <td class="dt-c"><span class="flux-badge" :class="fluxBadgeClass(it.play_method)">{{ it.play_method || '—' }}</span></td>
              <td class="dt-r dt-sec">{{ ticksToDuration(it.duration_ticks) }}</td>
              <td class="dt-r dt-muted">{{ it.started_at ? formatDate(it.started_at) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="activity.total > 25" class="tbl-pag">
        <span class="pag-info">{{ activity.items.length ? `${activityCursorHistory.length * 25 + 1}–${activityCursorHistory.length * 25 + activity.items.length}` : '0' }} {{ $t('common.of') }} {{ activity.total }}</span>
        <div class="pag-btns">
          <button class="pag-btn" :disabled="!activityCursorHistory.length" @click="activityFirstPage()"><ChevronsLeft :size="12" /></button>
          <button class="pag-btn" :disabled="!activityCursorHistory.length" @click="activityPrevPage()"><ChevronLeft :size="12" /></button>
          <span class="pag-cur">{{ activityCursorHistory.length + 1 }}</span>
          <button class="pag-btn pag-next" :disabled="!activity.has_more" @click="activityNextPage()"><ChevronRight :size="12" /></button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'
import { sortArrow, sortArrowClass, formatDate, fluxBadgeClass } from '@/components/stats/statsTableUtils'
import { ChevronLeft, ChevronRight, ChevronsLeft, Trash2 } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'
import '@/assets/styles/stats-tables.css'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { apiPost } = useApi()
const { activity, loadingActivity, loadActivity, minimap24h, loadMinimap24h, ticksToDuration } = useStats()
const { activitySearchSeed } = useStatsUI()

const activityCursorHistory = ref([])
const activitySearch = ref('')
const activitySortBy = ref('started_at')
const activitySortOrder = ref('desc')
const activityPerPage = ref(25)
let actDb = null

function fetchActivityData(cursor = '') { loadActivity({ cursor, limit: activityPerPage.value, search: activitySearch.value }) }
function activityNextPage() { const nc = activity.value.next_cursor; if (nc) { activityCursorHistory.value.push(''); fetchActivityData(nc) } }
function activityPrevPage() { if (activityCursorHistory.value.length) { activityCursorHistory.value.pop(); fetchActivityData('') } }
function activityFirstPage() { activityCursorHistory.value = []; fetchActivityData('') }
function debouncedFetchActivity() { clearTimeout(actDb); actDb = setTimeout(() => { activityCursorHistory.value = []; fetchActivityData('') }, 300) }

function toggleActivitySort(c) {
  if (activitySortBy.value === c) activitySortOrder.value = activitySortOrder.value === 'desc' ? 'asc' : 'desc'
  else { activitySortBy.value = c; activitySortOrder.value = 'desc' }
}

const sortedActivity = computed(() => {
  const it = [...(activity.value?.items || [])]
  if (activitySortBy.value === 'started_at' && activitySortOrder.value === 'desc') return it
  it.sort((a, b) => {
    let va = a[activitySortBy.value] || ''
    let vb = b[activitySortBy.value] || ''
    if (activitySortBy.value === 'duration') { va = a.duration_ticks || 0; vb = b.duration_ticks || 0 }
    if (typeof va === 'number') return activitySortOrder.value === 'desc' ? vb - va : va - vb
    return activitySortOrder.value === 'desc' ? String(vb).localeCompare(String(va)) : String(va).localeCompare(String(vb))
  })
  return it
})

const activitySelected = ref(new Set())
const activityAllChecked = computed(() => sortedActivity.value.length > 0 && sortedActivity.value.every(it => activitySelected.value.has(it.id)))
function toggleActivitySelect(id) {
  const s = new Set(activitySelected.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  activitySelected.value = s
}
function toggleActivitySelectAll() {
  if (activityAllChecked.value) activitySelected.value = new Set()
  else activitySelected.value = new Set(sortedActivity.value.map(it => it.id))
}
async function bulkDeleteActivity() {
  const ids = [...activitySelected.value]
  if (!ids.length) return
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('stats.confirmBulkDeleteActivity', { count: ids.length }),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  try { await apiPost('/api/stats/activity/bulk-delete', { ids }); activitySelected.value = new Set(); fetchActivityData('') } catch (e) { console.error('[StatsActivityTab.bulkDeleteActivity] failed to bulk-delete', e) }
}

const minimapStats = computed(() => ({ total: minimap24h.value.length }))
const minimapHourData = computed(() => {
  const items = minimap24h.value
  const hours = Array.from({ length: 24 }, () => ({ direct: 0, transcode: 0, other: 0, users: [] }))
  for (const i of items) {
    const h = new Date(i.started_at).getHours()
    if (i.play_method === 'DirectPlay') hours[h].direct++
    else if (i.play_method === 'Transcode') hours[h].transcode++
    else hours[h].other++
    if (!hours[h].users.includes(i.user)) hours[h].users.push(i.user)
  }
  const maxCount = Math.max(1, ...hours.map(h => h.direct + h.transcode + h.other))
  return hours.map((h, idx) => {
    const total = h.direct + h.transcode + h.other
    const dominant = h.transcode > h.direct ? '#fbbf24' : total > 0 ? '#4ade80' : 'transparent'
    return {
      pct: Math.round((total / maxCount) * 100),
      color: dominant,
      title: `${idx}h : ${total} lecture${total > 1 ? 's' : ''}${h.users.length ? ' (' + h.users.join(', ') + ')' : ''}`,
    }
  })
})

watch(activitySearchSeed, seed => {
  if (seed) {
    activitySearch.value = seed
    activityCursorHistory.value = []
    fetchActivityData('')
    activitySearchSeed.value = ''
  }
})

onMounted(() => {
  if (activitySearchSeed.value) {
    activitySearch.value = activitySearchSeed.value
    activitySearchSeed.value = ''
  }
  if (!activity.value.items.length || activitySearch.value) fetchActivityData('')
  if (!minimap24h.value.length) loadMinimap24h()
})
</script>

<style scoped>
.minimap-wrap { padding: 14px 16px; margin-bottom: 0; }
.minimap-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.minimap-title { font-size: var(--text-2xs); font-weight: var(--font-medium); color: var(--text-primary); }
.minimap-count { font-size: var(--text-2xs); color: var(--text-muted); }
.minimap-hours { display: flex; align-items: flex-end; gap: 3px; height: 48px; padding: 0 2px; }
.minimap-hour-col { flex: 1; min-width: 0; display: flex; align-items: flex-end; height: 100%; background: rgba(255,255,255,.02); border-radius: 3px 3px 0 0; cursor: default; transition: background var(--duration-fast); }
.minimap-hour-col:hover { background: var(--surface-3); }
.minimap-hour-fill { width: 100%; border-radius: 3px 3px 0 0; min-height: 0; transition: height var(--duration-slow) ease; }
.minimap-hlabels { display: flex; justify-content: space-between; padding: 4px 2px 0; }
.minimap-hlabel { font-size: .5rem; color: var(--text-muted); width: calc(100% / 8); text-align: center; }
.minimap-legend { display: flex; gap: 12px; margin-top: 8px; justify-content: center; }
.minimap-leg { display: flex; align-items: center; gap: 4px; font-size: .58rem; color: var(--text-muted); }
.minimap-ldot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.minimap-ldot-direct { background: #4ade80; }
.minimap-ldot-transcode { background: var(--color-warning); }
.minimap-ldot-other { background: #818cf8; }
.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }
.tbl-wrap-activity { margin-top: 12px; }
.col-w36 { width: 36px; }
.col-w9p { width: 9%; }
.col-w11p { width: 11%; }
.col-w13p { width: 13%; }
.col-w26p { width: 26%; }
</style>
