<template>
  <div>
    <div class="pt-admin-filters">
      <button
        v-for="st in statuses" :key="st"
        class="pt-filter-btn"
        :class="{ active: filter === st }"
        @click="filterBy(st)"
      >{{ $t(`portal.tickets.status.${st || 'all'}`) }}</button>
    </div>

    <div class="pt-admin-table">
      <div v-for="t in tickets" :key="t.id" class="pt-admin-row">
        <span class="pt-ticket-id">#{{ t.id }}</span>
        <span class="pt-ticket-type">{{ $t(`portal.tickets.types.${t.issue_type}`) }}</span>
        <span class="pt-ticket-media">{{ t.media_title }}</span>
        <span class="pt-ticket-status" :class="`pt-ts--${t.status}`">{{ t.status }}</span>
        <div class="pt-admin-actions">
          <select :value="t.status" class="pt-mini-select" @change="changeStatus(t.id, $event.target.value)">
            <option v-for="s in ['open','in_progress','resolved','closed']" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
      </div>
      <div v-if="!tickets.length" class="pt-empty">{{ $t('common.noResults') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePortalTickets } from '@/composables/portal/usePortalTickets'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'

const { tickets, fetchTickets, updateStatus } = usePortalTickets()
const { showToast } = useToast()
const { t } = useI18n()
const filter = ref('')
const statuses = ['', 'open', 'in_progress', 'resolved', 'closed']

async function filterBy(st) {
  filter.value = st
  await fetchTickets(st || null)
}

async function changeStatus(id, status) {
  await updateStatus(id, status)
  showToast(t('common.saved'), TOAST_TYPE.OK)
  await fetchTickets(filter.value || null)
}

onMounted(() => fetchTickets())
</script>

<style scoped>
.pt-admin-filters { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.pt-filter-btn { padding: 0.3rem 0.7rem; border-radius: var(--radius-btn); border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-muted); cursor: pointer; font-size: var(--portal-text-sm); }
.pt-filter-btn.active { border-color: var(--accent); color: var(--accent); }
.pt-admin-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.55rem 0.5rem; border-bottom: 1px solid var(--border); }
.pt-ticket-id { font-weight: var(--portal-font-bold); color: var(--text-muted); font-size: var(--portal-text-sm); width: 3rem; }
.pt-ticket-type { font-size: var(--portal-text-xs); color: var(--text-secondary); }
.pt-ticket-media { flex: 1; font-size: var(--portal-text-sm); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-ticket-status { font-size: var(--portal-text-2xs); font-weight: var(--portal-font-bold); text-transform: uppercase; }
.pt-ts--open { color: #eab308; }
.pt-ts--in_progress { color: var(--accent); }
.pt-ts--resolved { color: var(--portal-color-success); }
.pt-ts--closed { color: var(--text-muted); }
.pt-admin-actions { display: flex; gap: 0.4rem; }
.pt-mini-select { background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-primary); font-size: var(--portal-text-xs); padding: 0.2rem 0.4rem; }
.pt-empty { color: var(--text-muted); text-align: center; padding: 1.5rem 0; }
</style>
