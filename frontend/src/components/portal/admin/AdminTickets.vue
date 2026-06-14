<template>
  <div>
    <div class="pt-admin-filters">
      <button
        v-for="st in statuses"
        :key="st"
        type="button"
        class="pt-filter-btn"
        :class="{ active: filter === st }"
        @click="filterBy(st)"
      >
        {{ $t(`portal.tickets.status.${st || 'all'}`) }}
      </button>
      <div class="pt-admin-pager">
        <PortalPagination
          :page="page"
          :per-page="perPage"
          :total="total"
          :disabled="loading"
          @update:page="onPage"
          @update:per-page="onPerPage"
        />
      </div>
    </div>

    <div class="pt-admin-table">
      <div v-for="ticket in tickets" :key="ticket.id" class="pt-admin-row">
        <span class="pt-ticket-id">#{{ ticket.id }}</span>
        <span class="pt-ticket-type">{{ $t(`portal.tickets.types.${ticket.issue_type}`) }}</span>
        <span class="pt-ticket-media">{{ ticket.media_title }}</span>
        <span class="pt-ticket-status" :class="`pt-ts--${ticket.status}`">
          {{ $t(`portal.tickets.status.${ticket.status}`) }}
        </span>
        <div class="pt-admin-actions">
          <select
            :value="ticket.status"
            class="pt-mini-select"
            @change="changeStatus(ticket.id, $event.target.value)"
          >
            <option v-for="s in ['open', 'in_progress', 'resolved', 'closed']" :key="s" :value="s">
              {{ $t(`portal.tickets.status.${s}`) }}
            </option>
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
import PortalPagination from '@/components/portal/PortalPagination.vue'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'

const { tickets, total, fetchTickets, updateStatus, loading } = usePortalTickets()
const { showToast } = useToast()
const { t } = useI18n()
const filter = ref('')
const page = ref(1)
const perPage = ref(DEFAULT_PAGE_SIZE)
const statuses = ['', 'open', 'in_progress', 'resolved', 'closed']

function buildQuery() {
  return { status: filter.value || null, page: page.value, perPage: perPage.value }
}
async function load() {
  await fetchTickets(buildQuery())
}
async function reload() {
  page.value = 1
  await load()
}
async function filterBy(st) {
  filter.value = st
  await reload()
}
function onPage(p) {
  page.value = p
  load()
}
function onPerPage(size) {
  perPage.value = size
  reload()
}

async function changeStatus(id, status) {
  await updateStatus(id, status)
  showToast(t('common.saved'), TOAST_TYPE.OK)
  await load()
  // A status change can empty the active-filter page — step back so the
  // admin never lands on a blank page behind a populated pager.
  if (!tickets.value.length && page.value > 1) {
    page.value -= 1
    await load()
  }
}

onMounted(load)
</script>

<style scoped>
.pt-admin-filters {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.pt-filter-btn {
  padding: 0.3rem 0.7rem;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-sm);
}
.pt-filter-btn.active {
  border-color: var(--accent);
  color: var(--accent);
}
.pt-admin-pager {
  margin-left: auto;
}
.pt-admin-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-ticket-id {
  font-weight: var(--font-bold);
  color: var(--text-muted);
  font-size: var(--text-sm);
  width: 3rem;
}
.pt-ticket-type {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.pt-ticket-media {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pt-ticket-status {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
}
.pt-ts--open {
  color: var(--color-warning);
}
.pt-ts--in_progress {
  color: var(--accent);
}
.pt-ts--resolved {
  color: var(--color-success);
}
.pt-ts--closed {
  color: var(--text-muted);
}
.pt-admin-actions {
  display: flex;
  gap: 0.4rem;
}
.pt-mini-select {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  padding: 0.2rem 0.4rem;
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 1.5rem 0;
}
</style>
