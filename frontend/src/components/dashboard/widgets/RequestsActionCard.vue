<template>
  <div class="wg-req" :class="{ 'wg-req-editing': editing }">
    <div class="wg-req-head">
      <span class="wg-req-title">{{ $t('dashboard.portalAction.title') }}</span>
    </div>
    <div class="wg-req-grid">
      <StatTile
        :icon="Clock"
        :label="$t('dashboard.portalAction.pending')"
        :value="loading ? '—' : stats.pending_requests"
        accent="var(--color-warning)"
        route="/portal/requests"
        :disabled="editing"
      />
      <StatTile
        :icon="LifeBuoy"
        :label="$t('dashboard.portalAction.tickets')"
        :value="loading ? '—' : stats.open_tickets"
        accent="var(--color-info)"
        :route="{ path: '/admin/portal', query: { tab: 'tickets' } }"
        :disabled="editing"
      />
      <StatTile
        :icon="CircleCheck"
        :label="$t('dashboard.portalAction.approvedWeek')"
        :value="loading ? '—' : stats.approved_this_week"
        accent="var(--color-success)"
        route="/portal/requests"
        :disabled="editing"
      />
      <StatTile
        :icon="CircleX"
        :label="$t('dashboard.portalAction.rejectedWeek')"
        :value="loading ? '—' : stats.rejected_this_week"
        accent="var(--color-error)"
        route="/portal/requests"
        :disabled="editing"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Clock, LifeBuoy, CircleCheck, CircleX } from 'lucide-vue-next'
import { fetchApiResponse } from '@/composables/useApi'
import StatTile from './StatTile.vue'

defineProps({ editing: { type: Boolean, default: false } })

const loading = ref(true)
const stats = ref({
  pending_requests: 0,
  open_tickets: 0,
  approved_this_week: 0,
  rejected_this_week: 0,
})

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
  } catch {
    /* silent: widget stats fetch, card stays blank */
  }
  loading.value = false
})
</script>

<style scoped>
.wg-req {
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

.wg-req-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-width: 0;
  flex-shrink: 0;
}
.wg-req-title {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wg-req-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  flex: 1;
  min-height: 0;
}
</style>
