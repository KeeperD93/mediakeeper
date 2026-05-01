<template>
  <div class="wg-req" :class="{ 'wg-req-editing': editing }">
    <div class="wg-req-head">
      <span class="wg-req-title">{{ $t('dashboard.portalAction.title') }}</span>
      <button v-if="!editing" class="wg-req-head-link" @click="goTo('/admin/portal')">
        {{ $t('dashboard.portalAction.manage') }} <ChevronRight :size="12" />
      </button>
    </div>
    <div class="wg-req-grid">
      <button class="wg-req-tile" :disabled="editing" @click="goTo('/portal/requests')">
        <Clock :size="18" class="wg-req-ic wg-req-ic-pending" />
        <span class="wg-req-label">{{ $t('dashboard.portalAction.pending') }}</span>
        <span class="wg-req-val">{{ loading ? '—' : stats.pending_requests }}</span>
      </button>
      <button class="wg-req-tile" :disabled="editing" @click="goTo('/admin/portal', { tab: 'tickets' })">
        <LifeBuoy :size="18" class="wg-req-ic wg-req-ic-tickets" />
        <span class="wg-req-label">{{ $t('dashboard.portalAction.tickets') }}</span>
        <span class="wg-req-val">{{ loading ? '—' : stats.open_tickets }}</span>
      </button>
      <button class="wg-req-tile" :disabled="editing" @click="goTo('/portal/requests')">
        <CircleCheck :size="18" class="wg-req-ic wg-req-ic-ok" />
        <span class="wg-req-label">{{ $t('dashboard.portalAction.approvedWeek') }}</span>
        <span class="wg-req-val">{{ loading ? '—' : stats.approved_this_week }}</span>
      </button>
      <button class="wg-req-tile" :disabled="editing" @click="goTo('/portal/requests')">
        <CircleX :size="18" class="wg-req-ic wg-req-ic-ko" />
        <span class="wg-req-label">{{ $t('dashboard.portalAction.rejectedWeek') }}</span>
        <span class="wg-req-val">{{ loading ? '—' : stats.rejected_this_week }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, Clock, LifeBuoy, CircleCheck, CircleX } from 'lucide-vue-next'
import { fetchApiResponse } from '@/composables/useApi'

defineProps({ editing: { type: Boolean, default: false } })

const router = useRouter()

const loading = ref(true)
const stats = ref({
  pending_requests: 0,
  open_tickets: 0,
  approved_this_week: 0,
  rejected_this_week: 0,
})

function goTo(path, query) {
  router.push(query ? { path, query } : path)
}

onMounted(async () => {
  try {
    const res = await fetchApiResponse('/api/portal/admin/stats', {
      retryOn401: false,
      redirectOn401: false,
    })
    if (res && res.ok) {
      const d = await res.json().catch(() => null)
      if (d) stats.value = { ...stats.value, ...d }
    }
  } catch { /* silent: widget stats fetch, card stays blank */ }
  loading.value = false
})
</script>

<style scoped>
.wg-req {
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

.wg-req-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}
.wg-req-title {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wg-req-head-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 4px 12px;
  /* Push left of the absolute `.widget-badge-icon` (14px icon at right:10px) */
  margin-right: 22px;
  border-radius: var(--radius-pill);
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-strong);
  color: rgba(255,255,255,.6);
  font-size: var(--text-3xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all .18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  flex-shrink: 0;
}
@media (hover: hover) {
  .wg-req-head-link:hover { border-color: rgba(255,255,255,0.18); color: rgba(255,255,255,.85); transform: translateY(-1px); }
}
@media (max-width: 767px) {
  .wg-req-head-link { min-height: 32px; padding: 5px 14px; }
}

.wg-req-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.wg-req-tile {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 10px;
  row-gap: 2px;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: var(--radius-card);
  color: inherit;
  cursor: pointer;
  text-align: left;
  min-width: 0;
  min-height: 44px;
  transition: border-color var(--duration-base), background var(--duration-base), transform var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.wg-req-tile:disabled { cursor: move; }
@media (hover: hover) {
  .wg-req-tile:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--accent-500) 35%, transparent);
    background: rgba(var(--accent-rgb), 0.05);
  }
}
.wg-req-tile:not(:disabled):active { transform: scale(0.98); }

.wg-req-ic {
  grid-row: 1 / span 2;
  align-self: center;
  flex-shrink: 0;
}
.wg-req-ic-pending { color: var(--accent-500); }
.wg-req-ic-tickets { color: var(--color-info); }
.wg-req-ic-ok      { color: var(--color-success); }
.wg-req-ic-ko      { color: #f43f5e; }

.wg-req-label {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wg-req-val {
  font-size: 20px;
  font-weight: var(--font-medium);
  line-height: var(--lh-tight);
  color: var(--text-primary);
}
</style>
