<template>
  <div class="wg-evt" :class="{ 'wg-evt-editing': editing }">
    <div class="wg-evt-head">
      <span class="wg-evt-title">{{ $t('dashboard.portalEvents.title') }}</span>
    </div>

    <div v-if="loading" class="wg-evt-empty">{{ $t('common.loading') }}</div>
    <div v-else-if="!items.length" class="wg-evt-empty">{{ $t('dashboard.portalEvents.empty') }}</div>

    <div v-else class="wg-evt-list">
      <button
        v-for="ev in items" :key="ev.id"
        class="wg-evt-item"
        :disabled="editing"
        @click="openEvent(ev)"
      >
        <div class="wg-evt-date">
          <span class="wg-evt-day">{{ formatDay(ev.scheduled_at) }}</span>
          <span class="wg-evt-month">{{ formatMonth(ev.scheduled_at) }}</span>
          <span class="wg-evt-time">{{ formatTime(ev.scheduled_at) }}</span>
        </div>
        <div class="wg-evt-body">
          <div class="wg-evt-name">{{ ev.title }}</div>
          <div class="wg-evt-meta">
            <span class="wg-evt-kind" :class="`wg-evt-kind--${ev.kind}`">
              {{ $t(`portal.mkCalendar.kind.${ev.kind}`) }}
            </span>
            <span
              v-if="ev.creator_deleted || ev.creator_label"
              class="wg-evt-creator"
              :class="{ 'wg-evt-creator--anon': ev.creator_deleted }"
            >
              {{ ev.creator_deleted ? $t('portal.common.deletedUser') : ev.creator_label }}
            </span>
            <span v-if="acceptedCount(ev) > 0" class="wg-evt-count">
              <Users :size="11" /> {{ acceptedCount(ev) }}
            </span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Users } from 'lucide-vue-next'
import { fetchApiResponse } from '@/composables/useApi'
import { INVITATION_STATUS } from '@/constants/events'

defineProps({ editing: { type: Boolean, default: false } })

const router = useRouter()
const loading = ref(true)
const items = ref([])

function openEvent(ev) {
  router.push({ name: 'portal-rooms', params: { id: ev.id } })
}

function formatDay(iso) {
  if (!iso) return ''
  return new Date(iso).getDate().toString().padStart(2, '0')
}
function formatMonth(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { month: 'short' })
}
function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function acceptedCount(ev) {
  return (ev.invitations || []).filter((i) => i.status === INVITATION_STATUS.ACCEPTED).length
}

async function load() {
  loading.value = true
  try {
    const res = await fetchApiResponse('/api/portal/admin/events/upcoming?limit=5', {
      retryOn401: false,
      redirectOn401: false,
    })
    if (res && res.ok) {
      const d = await res.json().catch(() => null)
      if (d?.items) items.value = d.items
    }
  } catch { /* silent: widget fetch, card stays blank */ }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.wg-evt {
  background: var(--card-bg, var(--surface-1));
  border-radius: var(--radius-card);
  padding: 12px 14px;
  border: 0.5px solid var(--border-default);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
}

.wg-evt-head {
  display: flex;
  align-items: center;
  min-width: 0;
  flex-shrink: 0;
}
.wg-evt-title {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wg-evt-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: 12px;
  text-align: center;
}

.wg-evt-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.wg-evt-list::-webkit-scrollbar { width: 3px; }
.wg-evt-list::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 2px; }

.wg-evt-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: var(--radius-card);
  color: inherit;
  cursor: pointer;
  text-align: left;
  min-width: 0;
  transition: border-color var(--duration-base), background var(--duration-base), transform var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.wg-evt-item:disabled { cursor: move; }
@media (hover: hover) {
  .wg-evt-item:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--accent-500) 35%, transparent);
    background: rgba(var(--accent-rgb), 0.05);
  }
}
.wg-evt-item:not(:disabled):active { transform: scale(0.99); }

.wg-evt-date {
  flex-shrink: 0;
  width: 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  border-right: 1px solid var(--border-strong);
  padding-right: 8px;
}
.wg-evt-day {
  font-size: var(--text-md);
  font-weight: var(--font-extrabold);
  line-height: var(--lh-tight);
  color: var(--text-primary);
}
.wg-evt-month {
  font-size: 9px;
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color: var(--text-muted);
  margin-top: 2px;
}
.wg-evt-time {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin-top: 3px;
}

.wg-evt-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.wg-evt-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wg-evt-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-3xs);
  flex-wrap: wrap;
}
.wg-evt-kind {
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  font-size: 9px;
}
.wg-evt-kind--private { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
.wg-evt-kind--public { background: rgba(34, 197, 94, 0.2); color: #86efac; }
.wg-evt-creator {
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.wg-evt-count {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--text-muted);
}
</style>
