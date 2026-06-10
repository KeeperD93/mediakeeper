<template>
  <div class="tab-panel">
    <StatsActivityMinimap v-if="minimap24h.length" :items="minimap24h" />

    <div class="glass-card tbl-wrap tbl-wrap-activity">
      <div class="tbl-header">
        <h2 class="tbl-title">{{ $t('stats.activityHistory') }}</h2>
        <div class="tbl-controls">
          <StatsActivityUserFilter
            v-if="activityUsers.length"
            :users="activityUsers"
            :excluded-ids="excludedUserIds"
            @toggle="toggleUserFilter"
            @set-all="setAllUsersFilter"
          />
          <div class="tbl-ctrl">
            <span class="ctrl-lbl">{{ $t('common.showPerPage') }}</span>
            <select
              v-model="activityPerPage"
              class="ctrl-sel mk-select-chevron"
              @change="changePerPage"
            >
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
              <option :value="500">500</option>
            </select>
          </div>
          <input
            v-model="activitySearch"
            class="ctrl-search"
            :placeholder="$t('common.search')"
            @input="debouncedFetchActivity"
          />
        </div>
      </div>
      <p v-if="!isGrouped" class="act-flat-note">{{ $t('stats.flatSortNotice') }}</p>
      <div v-if="loadingActivity && !activity.items.length" class="tbl-loading">
        <div v-for="n in 5" :key="n" class="skel-tbl-row">
          <div class="skel-line w40" />
          <div class="skel-line w60" />
          <div class="skel-line w30" />
        </div>
      </div>
      <div v-else class="tbl-scroll">
        <table ref="tableRef" class="dt">
          <colgroup>
            <col v-for="(w, i) in colWidths" :key="i" :style="{ width: w + 'px' }" />
          </colgroup>
          <thead>
            <tr>
              <th class="dt-c">
                <input
                  v-indeterminate="activitySomeChecked"
                  type="checkbox"
                  class="act-chk"
                  :checked="activityAllChecked"
                  @change="toggleActivitySelectAll"
                />
              </th>
              <th class="dt-c" />
              <th class="sortable" @click="toggleActivitySort('user')">
                {{ $t('common.user') }}
                <span :class="sortArrowClass('user', activitySortBy)">
                  {{ sortArrow('user', activitySortBy, activitySortOrder) }}
                </span>
                <MkColResizer :index="2" @start="startResize" />
              </th>
              <th class="sortable" @click="toggleActivitySort('title')">
                {{ $t('stats.title') }}
                <span :class="sortArrowClass('title', activitySortBy)">
                  {{ sortArrow('title', activitySortBy, activitySortOrder) }}
                </span>
                <MkColResizer :index="3" @start="startResize" />
              </th>
              <th class="sortable" @click="toggleActivitySort('client')">
                {{ $t('common.client') }}
                <span :class="sortArrowClass('client', activitySortBy)">
                  {{ sortArrow('client', activitySortBy, activitySortOrder) }}
                </span>
                <MkColResizer :index="4" @start="startResize" />
              </th>
              <th>
                {{ $t('common.device') }}
                <MkColResizer :index="5" @start="startResize" />
              </th>
              <th class="sortable dt-c" @click="toggleActivitySort('play_method')">
                {{ $t('stats.stream') }}
                <span :class="sortArrowClass('play_method', activitySortBy)">
                  {{ sortArrow('play_method', activitySortBy, activitySortOrder) }}
                </span>
                <MkColResizer :index="6" @start="startResize" />
              </th>
              <th class="dt-r">
                {{ $t('common.durationLabel') }}
                <MkColResizer :index="7" @start="startResize" />
              </th>
              <th class="dt-r">
                {{ $t('stats.progress') }}
                <MkColResizer :index="8" @start="startResize" />
              </th>
              <th class="sortable dt-r" @click="toggleActivitySort('started_at')">
                {{ $t('common.date') }}
                <span :class="sortArrowClass('started_at', activitySortBy)">
                  {{ sortArrow('started_at', activitySortBy, activitySortOrder) }}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!activityItems.length">
              <td colspan="10" class="dt-empty">{{ $t('stats.noData') }}</td>
            </tr>
            <template v-for="it in activityItems" :key="it.id">
              <tr :class="{ 'act-row-selected': rowSelectState(it) !== 'none' }">
                <td class="dt-c">
                  <input
                    v-indeterminate="rowSelectState(it) === 'some'"
                    type="checkbox"
                    class="act-chk"
                    :checked="rowSelectState(it) === 'all'"
                    @change="toggleActivitySelect(it)"
                  />
                </td>
                <td class="dt-c">
                  <button
                    v-if="it.session_count > 1"
                    type="button"
                    class="act-exp"
                    :aria-expanded="isExpanded(it.id)"
                    :aria-label="
                      $t(isExpanded(it.id) ? 'stats.collapseGroup' : 'stats.expandGroup')
                    "
                    @click="toggleExpand(it.id)"
                  >
                    <Minus v-if="isExpanded(it.id)" :size="12" />
                    <Plus v-else :size="12" />
                  </button>
                </td>
                <td v-ellipsis-title class="dt-name">{{ it.user }}</td>
                <td v-ellipsis-title class="dt-sec">
                  {{ it.title }}
                  <span v-if="it.episode" class="dt-ep">{{ it.episode }}</span>
                </td>
                <td v-ellipsis-title class="dt-sec">{{ it.client || '—' }}</td>
                <td v-ellipsis-title class="dt-sec">{{ it.device || '—' }}</td>
                <td v-ellipsis-title class="dt-c">
                  <span class="flux-badge" :class="fluxBadgeClass(it.play_method)">
                    {{ it.play_method || '—' }}
                  </span>
                </td>
                <td v-ellipsis-title class="dt-r dt-sec">
                  {{ ticksToDuration(it.session_ticks) }}
                  <span
                    v-if="it.session_count > 1"
                    class="act-count"
                    :aria-label="$t('stats.groupSessions', { count: it.session_count })"
                  >
                    ({{ it.session_count }})
                  </span>
                </td>
                <td class="dt-r">
                  <StatsActivitySegmentBar
                    v-if="it.session_count > 1"
                    :position="it.max_position_ticks"
                    :runtime="it.runtime_ticks"
                    :sessions="it.sessions"
                  />
                  <StatsActivityProgress
                    v-else
                    :position="it.position_ticks"
                    :runtime="it.runtime_ticks"
                  />
                </td>
                <td v-ellipsis-title class="dt-r dt-muted">
                  {{ it.started_at ? formatDate(it.started_at) : '—' }}
                </td>
              </tr>
              <tr
                v-for="s in isExpanded(it.id) && it.sessions ? it.sessions.slice(1) : []"
                :key="s.id"
                class="act-child"
                :class="{ 'act-row-selected': activitySelected.has(s.id) }"
              >
                <td class="dt-c">
                  <input
                    type="checkbox"
                    class="act-chk"
                    :checked="activitySelected.has(s.id)"
                    @change="toggleSessionSelect(s.id)"
                  />
                </td>
                <td class="dt-c"><span class="act-child-mark" aria-hidden="true">↳</span></td>
                <td class="dt-name" />
                <td class="dt-sec" />
                <td v-ellipsis-title class="dt-sec">{{ s.client || '—' }}</td>
                <td v-ellipsis-title class="dt-sec">{{ s.device || '—' }}</td>
                <td v-ellipsis-title class="dt-c">
                  <span class="flux-badge" :class="fluxBadgeClass(s.play_method)">
                    {{ s.play_method || '—' }}
                  </span>
                </td>
                <td v-ellipsis-title class="dt-r dt-sec">{{ ticksToDuration(s.session_ticks) }}</td>
                <td class="dt-r">
                  <StatsActivityProgress :position="s.position_ticks" :runtime="s.runtime_ticks" />
                </td>
                <td v-ellipsis-title class="dt-r dt-muted">
                  {{ s.started_at ? formatDate(s.started_at) : '—' }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-if="canPrev || canNext" class="tbl-pag">
        <span class="pag-info">
          <template v-if="isGrouped">{{ activity.total }} {{ $t('stats.sessionsTotal') }}</template>
          <template v-else>
            {{ flatRangeStart }}–{{ flatRangeEnd }} {{ $t('common.of') }} {{ activity.total }}
          </template>
        </span>
        <div class="pag-btns">
          <button class="pag-btn" :disabled="!canPrev" @click="activityFirstPage()">
            <ChevronsLeft :size="12" />
          </button>
          <button class="pag-btn" :disabled="!canPrev" @click="activityPrevPage()">
            <ChevronLeft :size="12" />
          </button>
          <span class="pag-cur">{{ pageNumber }}</span>
          <button class="pag-btn pag-next" :disabled="!canNext" @click="activityNextPage()">
            <ChevronRight :size="12" />
          </button>
        </div>
      </div>
    </div>

    <MkBulkBar :count="activitySelected.size">
      <template #count>
        {{ $t('stats.bulkSelected', activitySelected.size, { n: activitySelected.size }) }}
      </template>
      <MkButton variant="danger" icon="trash-2" @click="bulkDeleteActivity">
        {{ $t('common.delete') }}
      </MkButton>
    </MkBulkBar>
  </div>
</template>

<script setup>
import { onMounted, nextTick, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, ChevronsLeft, Minus, Plus } from 'lucide-vue-next'
import { useStats } from '@/composables/useStats'
import { useStatsActivityTable } from '@/composables/useStatsActivityTable'
import { useColumnResize } from '@/composables/useColumnResize'
import {
  sortArrow,
  sortArrowClass,
  formatDate,
  fluxBadgeClass,
} from '@/components/stats/statsTableUtils'
import MkBulkBar from '@/components/common/MkBulkBar.vue'
import MkButton from '@/components/common/MkButton.vue'
import MkColResizer from '@/components/common/MkColResizer.vue'
import StatsActivityMinimap from '@/components/stats/StatsActivityMinimap.vue'
import StatsActivityProgress from '@/components/stats/StatsActivityProgress.vue'
import StatsActivitySegmentBar from '@/components/stats/StatsActivitySegmentBar.vue'
import StatsActivityUserFilter from '@/components/stats/StatsActivityUserFilter.vue'
import '@/assets/styles/stats-tables.css'

// Reflect a partial group selection on the parent checkbox (DOM-only prop).
const vIndeterminate = {
  mounted: (el, b) => (el.indeterminate = b.value),
  updated: (el, b) => (el.indeterminate = b.value),
}

// Native tooltip only when a cell's text is actually clipped — re-checked on
// hover so it stays accurate after a column resize. No tooltip when it fits.
const vEllipsisTitle = {
  mounted(el) {
    el.__truncCheck = () => {
      el.title = el.scrollWidth > el.clientWidth ? el.textContent.replace(/\s+/g, ' ').trim() : ''
    }
    el.addEventListener('mouseenter', el.__truncCheck)
  },
  unmounted(el) {
    if (el.__truncCheck) el.removeEventListener('mouseenter', el.__truncCheck)
  },
}

const { minimap24h, loadMinimap24h } = useStats()
const {
  activity,
  loadingActivity,
  ticksToDuration,
  activitySearch,
  activitySortBy,
  activitySortOrder,
  activityPerPage,
  activitySelected,
  activityUsers,
  excludedUserIds,
  activityItems,
  isGrouped,
  activityAllChecked,
  activitySomeChecked,
  canPrev,
  canNext,
  pageNumber,
  flatRangeStart,
  flatRangeEnd,
  changePerPage,
  debouncedFetchActivity,
  activityFirstPage,
  activityPrevPage,
  activityNextPage,
  toggleActivitySort,
  isExpanded,
  toggleExpand,
  rowSelectState,
  toggleActivitySelect,
  toggleSessionSelect,
  toggleActivitySelectAll,
  bulkDeleteActivity,
  toggleUserFilter,
  setAllUsersFilter,
} = useStatsActivityTable()

// Resizable columns (checkbox + expander first, then the 8 data columns).
const tableRef = ref(null)
const ACTIVITY_COLS = [40, 44, 103, 335, 153, 215, 177, 75, 351, 91]
const {
  widths: colWidths,
  ready: colsReady,
  init: initColWidths,
  startResize,
} = useColumnResize(ACTIVITY_COLS, { min: 32, fixed: 2, persistKey: 'stats.activity' })

// Fit columns to the container once the table is actually in the DOM (it isn't
// during the loading skeleton). Idempotent via the colsReady guard.
let fitting = false
async function fitColumns() {
  if (colsReady.value || fitting) return
  fitting = true
  try {
    await nextTick()
    const c = tableRef.value?.parentElement?.clientWidth
    if (c) await initColWidths(c)
  } finally {
    fitting = false
  }
}
onMounted(() => {
  if (!minimap24h.value.length) loadMinimap24h()
  fitColumns()
})
watch(loadingActivity, v => {
  if (!v) fitColumns()
})
</script>

<style scoped>
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.tbl-wrap-activity {
  margin-top: 12px;
}
</style>
