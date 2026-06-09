<template>
  <div class="tab-panel">
    <StatsActivityMinimap v-if="minimap24h.length" :items="minimap24h" />

    <div class="glass-card tbl-wrap tbl-wrap-activity">
      <div class="tbl-header">
        <h2 class="tbl-title">{{ $t('stats.activityHistory') }}</h2>
        <MkButton
          v-if="activitySelected.size"
          variant="danger"
          icon="trash-2"
          @click="bulkDeleteActivity"
        >
          {{ $t('common.delete') }} ({{ activitySelected.size }})
        </MkButton>
        <div class="tbl-controls">
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
      <div v-if="activityUsers.length" class="act-uf">
        <span class="act-uf-lbl">{{ $t('stats.filterUsers') }}</span>
        <button
          v-for="u in activityUsers"
          :key="u.id"
          type="button"
          class="act-uf-chip"
          :class="{ 'act-uf-off': excludedUserIds.has(u.id) }"
          :aria-pressed="!excludedUserIds.has(u.id)"
          @click="toggleUserFilter(u.id)"
        >
          {{ u.name }}
        </button>
      </div>
      <div v-if="loadingActivity && !activity.items.length" class="tbl-loading">
        <div v-for="n in 5" :key="n" class="skel-tbl-row">
          <div class="skel-line w40" />
          <div class="skel-line w60" />
          <div class="skel-line w30" />
        </div>
      </div>
      <div v-else class="tbl-scroll">
        <table class="dt">
          <colgroup>
            <col class="col-w36" />
            <col class="col-w11p" />
            <col class="col-w18p" />
            <col class="col-w11p" />
            <col class="col-w13p" />
            <col class="col-w9p" />
            <col class="col-w11p" />
            <col class="col-w13p" />
            <col class="col-w11p" />
          </colgroup>
          <thead>
            <tr>
              <th class="dt-c">
                <input
                  type="checkbox"
                  class="act-chk"
                  :checked="activityAllChecked"
                  @change="toggleActivitySelectAll"
                />
              </th>
              <th class="sortable" @click="toggleActivitySort('user')">
                {{ $t('common.user') }}
                <span :class="sortArrowClass('user', activitySortBy)">
                  {{ sortArrow('user', activitySortBy, activitySortOrder) }}
                </span>
              </th>
              <th class="sortable" @click="toggleActivitySort('title')">
                {{ $t('stats.title') }}
                <span :class="sortArrowClass('title', activitySortBy)">
                  {{ sortArrow('title', activitySortBy, activitySortOrder) }}
                </span>
              </th>
              <th class="sortable" @click="toggleActivitySort('client')">
                {{ $t('common.client') }}
                <span :class="sortArrowClass('client', activitySortBy)">
                  {{ sortArrow('client', activitySortBy, activitySortOrder) }}
                </span>
              </th>
              <th>{{ $t('common.device') }}</th>
              <th class="sortable dt-c" @click="toggleActivitySort('play_method')">
                {{ $t('stats.stream') }}
                <span :class="sortArrowClass('play_method', activitySortBy)">
                  {{ sortArrow('play_method', activitySortBy, activitySortOrder) }}
                </span>
              </th>
              <th class="sortable dt-r" @click="toggleActivitySort('duration')">
                {{ $t('common.durationLabel') }}
                <span :class="sortArrowClass('duration', activitySortBy)">
                  {{ sortArrow('duration', activitySortBy, activitySortOrder) }}
                </span>
              </th>
              <th class="dt-r">{{ $t('stats.progress') }}</th>
              <th class="sortable dt-r" @click="toggleActivitySort('started_at')">
                {{ $t('common.date') }}
                <span :class="sortArrowClass('started_at', activitySortBy)">
                  {{ sortArrow('started_at', activitySortBy, activitySortOrder) }}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!sortedActivity.length">
              <td colspan="9" class="dt-empty">{{ $t('stats.noData') }}</td>
            </tr>
            <tr
              v-for="it in sortedActivity"
              :key="it.id"
              :class="{ 'act-row-selected': activitySelected.has(it.id) }"
            >
              <td class="dt-c">
                <input
                  type="checkbox"
                  class="act-chk"
                  :checked="activitySelected.has(it.id)"
                  @change="toggleActivitySelect(it.id)"
                />
              </td>
              <td class="dt-name">{{ it.user }}</td>
              <td class="dt-sec">
                {{ it.title }}
                <span v-if="it.episode" class="dt-ep">{{ it.episode }}</span>
              </td>
              <td class="dt-sec">{{ it.client || '—' }}</td>
              <td class="dt-sec">{{ it.device || '—' }}</td>
              <td class="dt-c">
                <span class="flux-badge" :class="fluxBadgeClass(it.play_method)">
                  {{ it.play_method || '—' }}
                </span>
              </td>
              <td class="dt-r dt-sec">{{ ticksToDuration(it.session_ticks) }}</td>
              <td class="dt-r">
                <StatsActivityProgress :position="it.position_ticks" :runtime="it.runtime_ticks" />
              </td>
              <td class="dt-r dt-muted">{{ it.started_at ? formatDate(it.started_at) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="activity.total > 25" class="tbl-pag">
        <span class="pag-info">
          {{
            activity.items.length
              ? `${activityCursorHistory.length * 25 + 1}–${activityCursorHistory.length * 25 + activity.items.length}`
              : '0'
          }}
          {{ $t('common.of') }} {{ activity.total }}
        </span>
        <div class="pag-btns">
          <button
            class="pag-btn"
            :disabled="!activityCursorHistory.length"
            @click="activityFirstPage()"
          >
            <ChevronsLeft :size="12" />
          </button>
          <button
            class="pag-btn"
            :disabled="!activityCursorHistory.length"
            @click="activityPrevPage()"
          >
            <ChevronLeft :size="12" />
          </button>
          <span class="pag-cur">{{ activityCursorHistory.length + 1 }}</span>
          <button
            class="pag-btn pag-next"
            :disabled="!activity.has_more"
            @click="activityNextPage()"
          >
            <ChevronRight :size="12" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { ChevronLeft, ChevronRight, ChevronsLeft } from 'lucide-vue-next'
import { useStats } from '@/composables/useStats'
import { useStatsActivityTable } from '@/composables/useStatsActivityTable'
import {
  sortArrow,
  sortArrowClass,
  formatDate,
  fluxBadgeClass,
} from '@/components/stats/statsTableUtils'
import MkButton from '@/components/common/MkButton.vue'
import StatsActivityMinimap from '@/components/stats/StatsActivityMinimap.vue'
import StatsActivityProgress from '@/components/stats/StatsActivityProgress.vue'
import '@/assets/styles/stats-tables.css'

const { minimap24h, loadMinimap24h } = useStats()
const {
  activity,
  loadingActivity,
  ticksToDuration,
  activityCursorHistory,
  activitySearch,
  activitySortBy,
  activitySortOrder,
  activityPerPage,
  activitySelected,
  activityUsers,
  excludedUserIds,
  sortedActivity,
  activityAllChecked,
  changePerPage,
  debouncedFetchActivity,
  activityFirstPage,
  activityPrevPage,
  activityNextPage,
  toggleActivitySort,
  toggleActivitySelect,
  toggleActivitySelectAll,
  bulkDeleteActivity,
  toggleUserFilter,
} = useStatsActivityTable()

onMounted(() => {
  if (!minimap24h.value.length) loadMinimap24h()
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
.col-w36 {
  width: 36px;
}
.col-w9p {
  width: 9%;
}
.col-w11p {
  width: 11%;
}
.col-w13p {
  width: 13%;
}
.col-w18p {
  width: 18%;
}
.act-uf {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 10px 14px 0;
}
.act-uf-lbl {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.act-uf-chip {
  padding: 3px 10px;
  font-size: var(--text-2xs);
  color: var(--text-primary);
  background: rgb(var(--accent-rgb), 0.16);
  border: none;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition:
    background var(--duration-fast),
    opacity var(--duration-fast);
}
.act-uf-chip.act-uf-off {
  background: var(--surface-3);
  color: var(--text-muted);
  text-decoration: line-through;
  opacity: 0.7;
}
</style>
