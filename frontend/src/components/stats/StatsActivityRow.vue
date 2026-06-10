<template>
  <tr :class="{ 'act-row-selected': selectState !== 'none' }">
    <td class="dt-c">
      <input
        v-indeterminate="selectState === 'some'"
        type="checkbox"
        class="act-chk"
        :checked="selectState === 'all'"
        @change="$emit('toggle-select', item)"
      />
    </td>
    <td class="dt-c">
      <button
        v-if="item.session_count > 1"
        type="button"
        class="act-exp"
        :aria-expanded="expanded"
        :aria-label="$t(expanded ? 'stats.collapseGroup' : 'stats.expandGroup')"
        @click="$emit('toggle-expand', item.id)"
      >
        <Minus v-if="expanded" :size="12" />
        <Plus v-else :size="12" />
      </button>
    </td>
    <td v-ellipsis-title class="dt-name">{{ item.user }}</td>
    <td v-ellipsis-title class="dt-sec">
      {{ item.title }}
      <span v-if="item.episode" class="dt-ep">{{ item.episode }}</span>
    </td>
    <td v-ellipsis-title class="dt-sec">{{ item.client || '—' }}</td>
    <td v-ellipsis-title class="dt-sec">{{ item.device || '—' }}</td>
    <td v-ellipsis-title class="dt-c">
      <span class="flux-badge" :class="fluxBadgeClass(item.play_method)">
        {{ item.play_method || '—' }}
      </span>
    </td>
    <td v-ellipsis-title class="dt-r dt-sec">
      {{ ticksToDuration(item.session_ticks) }}
      <span
        v-if="item.session_count > 1"
        class="act-count"
        :aria-label="$t('stats.groupSessions', { count: item.session_count })"
      >
        ({{ item.session_count }})
      </span>
    </td>
    <td class="dt-r">
      <StatsActivitySegmentBar
        v-if="item.session_count > 1"
        :position="item.max_position_ticks"
        :runtime="item.runtime_ticks"
        :sessions="item.sessions"
      />
      <StatsActivityProgress v-else :position="item.position_ticks" :runtime="item.runtime_ticks" />
    </td>
    <td v-ellipsis-title class="dt-r dt-muted">
      {{ item.started_at ? formatDate(item.started_at) : '—' }}
    </td>
  </tr>
  <tr
    v-for="s in expanded && item.sessions ? item.sessions.slice(1) : []"
    :key="s.id"
    class="act-child"
    :class="{ 'act-row-selected': selectedIds.has(s.id) }"
  >
    <td class="dt-c">
      <input
        type="checkbox"
        class="act-chk"
        :checked="selectedIds.has(s.id)"
        @change="$emit('toggle-session', s.id)"
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

<script setup>
import { Minus, Plus } from 'lucide-vue-next'
import { useStats } from '@/composables/useStats'
import { formatDate, fluxBadgeClass } from '@/components/stats/statsTableUtils'
import { vIndeterminate, vEllipsisTitle } from '@/directives/tableCell'
import StatsActivityProgress from '@/components/stats/StatsActivityProgress.vue'
import StatsActivitySegmentBar from '@/components/stats/StatsActivitySegmentBar.vue'

// One grouped parent row + its expanded child sessions. Selection/expand state
// is owned by the table; this component is presentational and emits intents.
defineProps({
  item: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  selectState: { type: String, default: 'none' }, // none | some | all
  selectedIds: { type: Object, default: () => new Set() }, // selected session ids
})
defineEmits(['toggle-expand', 'toggle-select', 'toggle-session'])

const { ticksToDuration } = useStats()
</script>
