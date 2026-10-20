<template>
  <div class="ptl">
    <header class="ptl-head">
      <div>
        <h1 class="ptl-title">{{ $t('portal.tickets.title') }}</h1>
        <p class="ptl-sub">{{ $t('portal.tickets.subtitle') }}</p>
      </div>
      <button class="ptl-create" type="button" @click="showForm = true">
        <Plus :size="16" :stroke-width="2.5" />
        {{ $t('portal.tickets.create') }}
      </button>
    </header>

    <div class="ptl-toolbar">
      <div class="arr-pills ptl-toolbar-pills">
        <button
          v-for="st in STATUS_OPTIONS"
          :key="`status-${st.value || 'all'}`"
          type="button"
          class="arr-pill"
          :class="{ 'arr-pill--active': statusFilter === st.value }"
          :aria-pressed="statusFilter === st.value ? 'true' : 'false'"
          @click="setStatus(st.value)"
        >
          {{ $t(st.label) }}
        </button>
      </div>
      <div class="ptl-toolbar-selects">
        <select
          v-model="issueFilter"
          class="arr-sort ptl-toolbar-select mk-select-chevron"
          :aria-label="$t('portal.tickets.issueType')"
          @change="onIssueChange"
        >
          <option value="">{{ $t('portal.tickets.list.filterTypeAll') }}</option>
          <option v-for="it in TICKET_ISSUE_TYPES" :key="it" :value="it">
            {{ $t(`portal.tickets.types.${it}`) }}
          </option>
        </select>
        <select
          v-model="sortOrder"
          class="arr-sort ptl-toolbar-select mk-select-chevron"
          :aria-label="$t('portal.tickets.list.sortLabel')"
          @change="onSortChange"
        >
          <option :value="TICKET_SORT.NEWEST">{{ $t('portal.tickets.list.sortNewest') }}</option>
          <option :value="TICKET_SORT.OLDEST">{{ $t('portal.tickets.list.sortOldest') }}</option>
        </select>
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

    <p v-if="total" class="ptl-count">
      {{ $t('portal.tickets.list.count', total) }}
    </p>

    <div v-if="!tickets.length" class="ptl-empty">
      <span class="ptl-empty-icon">
        <CircleCheck :size="28" :stroke-width="1.6" aria-hidden="true" />
      </span>
      <p class="ptl-empty-title">{{ $t('portal.tickets.list.emptyTitle') }}</p>
      <p class="ptl-empty-sub">{{ $t('portal.tickets.list.emptySub') }}</p>
    </div>

    <div v-else class="ptl-list">
      <TicketCard v-for="ticket in tickets" :key="ticket.id" :ticket="ticket" @open="openTicket" />
    </div>

    <TicketCreateModal
      v-if="showForm"
      :busy="creating"
      @close="showForm = false"
      @submit="createFromForm"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortalTickets } from '@/composables/portal/usePortalTickets'
import { resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import TicketCard from '@/components/portal/tickets/TicketCard.vue'
import TicketCreateModal from '@/components/portal/tickets/TicketCreateModal.vue'
import PortalPagination from '@/components/portal/PortalPagination.vue'
import { PORTAL_TAB } from '@/constants/portal'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'
import { TICKET_ISSUE_TYPES, TICKET_SORT, TICKET_STATUS } from '@/constants/tickets'
import { CircleCheck, Plus } from 'lucide-vue-next'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/tickets-list.css'

const { tickets, total, fetchTickets, createTicket, loading } = usePortalTickets()
const { showToast } = useToast()
const { t } = useI18n()
const router = useRouter()

const showForm = ref(false)
const creating = ref(false)
const statusFilter = ref('')
const issueFilter = ref('')
const sortOrder = ref(TICKET_SORT.NEWEST)
const page = ref(1)
const perPage = ref(DEFAULT_PAGE_SIZE)

const STATUS_OPTIONS = [
  { value: '', label: 'portal.tickets.status.all' },
  ...Object.values(TICKET_STATUS).map(value => ({
    value,
    label: `portal.tickets.status.${value}`,
  })),
]

function buildFilters() {
  return {
    status: statusFilter.value || null,
    issueTypes: issueFilter.value ? [issueFilter.value] : null,
    sort: sortOrder.value,
    page: page.value,
    perPage: perPage.value,
  }
}

async function load() {
  await fetchTickets(buildFilters())
}
// Any status/type/sort/size change returns to the first page.
async function reload() {
  page.value = 1
  await load()
}
async function setStatus(value) {
  statusFilter.value = value
  await reload()
}
function onIssueChange() {
  reload()
}
function onSortChange() {
  reload()
}
function onPage(p) {
  page.value = p
  load()
}
function onPerPage(size) {
  perPage.value = size
  reload()
}

function openTicket(id) {
  router.push({ name: PORTAL_TAB.TICKET_DETAIL, params: { id } })
}

async function createFromForm(payload) {
  creating.value = true
  try {
    const res = await createTicket(payload)
    if (!res?.success) return
    showToast(t('common.success'), TOAST_TYPE.OK)
    showForm.value = false
    await reload()
  } catch (e) {
    // The form stays open with what was typed.
    console.error('[PortalTickets.createFromForm]', e)
    showToast(resolveApiError(e.message, 'portal.tickets.createFailed'), TOAST_TYPE.ERR)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>
