<template>
  <div class="wg-evt" :class="{ 'wg-evt-editing': editing }">
    <div class="wg-evt-head">
      <span class="wg-evt-title">{{ $t('dashboard.portalEvents.title') }}</span>
    </div>

    <div v-if="loading" class="wg-evt-empty">{{ $t('common.loading') }}</div>
    <div v-else-if="!items.length" class="wg-evt-empty">
      {{ $t('dashboard.portalEvents.empty') }}
    </div>

    <div v-else class="wg-evt-list">
      <button
        v-for="ev in items"
        :key="ev.id"
        class="wg-evt-item"
        :class="`wg-evt-item--${ev.kind}`"
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
              <Users :size="11" />
              {{ acceptedCount(ev) }}
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
  return (ev.invitations || []).filter(i => i.status === INVITATION_STATUS.ACCEPTED).length
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
  } catch {
    /* silent: widget fetch, card stays blank */
  }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.wg-evt {
  background: var(--card-bg);
  border-radius: var(--radius-card);
  padding: var(--space-3) var(--space-3-5);
  border: var(--border-width-thin) solid var(--border-default);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5);
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
  letter-spacing: var(--tracking-widest);
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
  padding: var(--space-3);
  text-align: center;
}

.wg-evt-list {
  display: flex;
  flex-direction: column;
  /* 6 px between rows — between --space-1 (4) and --space-2 (8) to
     keep the date pills snug without touching. */
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.wg-evt-list::-webkit-scrollbar {
  /* 3 px scrollbar — narrower than --scrollbar-width (6) for the
     compact list view. Widget-local. */
  width: 3px;
}
.wg-evt-list::-webkit-scrollbar-thumb {
  background: var(--surface-3);
  border-radius: 2px;
}

.wg-evt-item {
  /* Hover tint flows from the event kind so the colour-coding of the
     PRIVÉ / PUBLIC badge extends to the whole row. Defaults to the
     global accent when no kind class is applied. */
  --wg-evt-hover: var(--accent-500);
  --wg-evt-hover-rgb: var(--accent-rgb);
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  padding: var(--space-2) var(--space-2-5);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-default);
  border-radius: var(--radius-card);
  color: inherit;
  cursor: pointer;
  text-align: left;
  min-width: 0;
  transition:
    border-color var(--duration-base),
    background var(--duration-base),
    transform var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.wg-evt-item--private {
  --wg-evt-hover: var(--color-info);
  --wg-evt-hover-rgb: var(--color-info-rgb);
}
.wg-evt-item--public {
  --wg-evt-hover: var(--color-online);
  --wg-evt-hover-rgb: var(--color-online-rgb);
}
.wg-evt-item:disabled {
  cursor: move;
}
@media (hover: hover) {
  .wg-evt-item:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--wg-evt-hover) 35%, transparent);
    background: rgb(var(--wg-evt-hover-rgb), 0.05);
  }
}
.wg-evt-item:not(:disabled):active {
  transform: scale(0.99);
}

.wg-evt-date {
  flex-shrink: 0;
  /* 48 px date column — fits "DD" + "MOIS" + "HH:MM" stacked without
     wrapping. Widget-local. */
  width: 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  border-right: var(--border-width) solid var(--border-strong);
  padding-right: var(--space-2);
}
.wg-evt-day {
  font-size: var(--text-md);
  font-weight: var(--font-extrabold);
  line-height: var(--lh-tight);
  color: var(--text-primary);
}
.wg-evt-month {
  /* 9 px micro-label below --text-3xs (~9.9 px) — kept literal so
     the date block stays compact. */
  font-size: 9px;
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color: var(--text-muted);
  margin-top: var(--space-half);
}
.wg-evt-time {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  /* 3 px nudge — between --space-half (2) and --space-1 (4). */
  margin-top: 3px;
}

.wg-evt-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  /* 3 px between name and meta — tighter than --space-1. */
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
  /* 6 px between meta chips — between --space-1 and --space-2. */
  gap: 6px;
  font-size: var(--text-3xs);
  flex-wrap: wrap;
}
.wg-evt-kind {
  /* 1 / 6 px chip padding — vertical sub-token, horizontal between
     --space-1 and --space-2. Hero-mini chip. */
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  /* 9 px label — matches .wg-evt-month for visual rhythm. */
  font-size: 9px;
}
.wg-evt-kind--private {
  background: rgb(var(--color-info-rgb), 0.2);
  color: var(--color-info-light);
}
.wg-evt-kind--public {
  background: rgb(var(--color-online-rgb), 0.2);
  color: var(--color-success-light);
}
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
  /* 3 px gap between icon and number — Users icon is 11 px, so
     anything larger would feel airy. */
  gap: 3px;
  color: var(--text-muted);
}
</style>
