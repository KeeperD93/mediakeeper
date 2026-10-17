<template>
  <div class="arr-page">
    <header class="arr-head">
      <div>
        <h2 class="arr-title">
          <span class="arr-title-accent" aria-hidden="true" />
          {{ $t('portal.admin.req.title') }}
        </h2>
        <p class="arr-sub">{{ $t('portal.admin.req.subtitle') }}</p>
      </div>
    </header>

    <!-- Top stats -->
    <div class="arr-stats">
      <div class="arr-stat arr-stat--pending">
        <span class="arr-stat-value">{{ stats?.pending_requests ?? '—' }}</span>
        <span class="arr-stat-label">{{ $t('portal.admin.req.statPending') }}</span>
        <span v-if="stats?.total_requests != null" class="arr-stat-total">
          {{ $t('portal.admin.req.statTotalSince', { count: stats.total_requests }) }}
        </span>
      </div>
      <div class="arr-stat arr-stat--approved">
        <span class="arr-stat-value">{{ stats?.approved_this_week ?? '—' }}</span>
        <span class="arr-stat-label">{{ $t('portal.admin.req.statApprovedWeek') }}</span>
        <span v-if="stats?.approved_total != null" class="arr-stat-total">
          {{ $t('portal.admin.req.statTotalSince', { count: stats.approved_total }) }}
        </span>
      </div>
      <div class="arr-stat arr-stat--rejected">
        <span class="arr-stat-value">{{ stats?.rejected_this_week ?? '—' }}</span>
        <span class="arr-stat-label">{{ $t('portal.admin.req.statRejectedWeek') }}</span>
        <span v-if="stats?.rejected_total != null" class="arr-stat-total">
          {{ $t('portal.admin.req.statTotalSince', { count: stats.rejected_total }) }}
        </span>
      </div>
      <div class="arr-stat arr-stat--available">
        <span class="arr-stat-value">{{ stats?.available_count ?? '—' }}</span>
        <span class="arr-stat-label">{{ $t('portal.admin.req.statAvailable') }}</span>
        <span v-if="stats?.available_total != null" class="arr-stat-total">
          {{ $t('portal.admin.req.statTotalSince', { count: stats.available_total }) }}
        </span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="arr-toolbar">
      <AdminRequestsFilters
        :status="filter"
        :media-type="typeFilter"
        :hide-available="hideAvailable"
        @update:status="setFilter"
        @update:media-type="onTypeFilter"
        @update:hide-available="setHideAvailable"
      />
      <select
        v-model="sortKey"
        class="arr-sort mk-select-chevron"
        :aria-label="$t('portal.admin.req.sortLabel')"
        @change="onSortChange"
      >
        <option :value="REQUEST_SORT.RECENT">{{ $t('portal.admin.req.sortRecent') }}</option>
        <option :value="REQUEST_SORT.OLDEST">{{ $t('portal.admin.req.sortOldest') }}</option>
        <option :value="REQUEST_SORT.TITLE">{{ $t('portal.admin.req.sortTitle') }}</option>
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

    <div v-if="loading" class="arr-loading"><MkSpinner size="md" /></div>

    <div v-else-if="!requests.length" class="arr-empty">
      {{ $t('common.noResults') }}
    </div>

    <div v-else class="arr-list">
      <AdminRequestsRow
        v-for="(req, idx) in requests"
        :key="req.id"
        :req="req"
        :index="(page - 1) * perPage + idx + 1"
        :busy="busyIds.has(req.id)"
        @action="onAction(req, $event)"
        @delete="onDelete(req)"
      />
    </div>

    <RejectReasonModal
      :open="!!rejectTarget"
      :media-title="rejectTarget?.title || ''"
      @confirm="onRejectConfirm"
      @cancel="cancelReject"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalRequests } from '@/composables/portal/usePortalRequests'
import { usePortalAdmin } from '@/composables/portal/usePortalAdmin'
import { useAdminRequestActions } from '@/composables/portal/useAdminRequestActions'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import AdminRequestsFilters from '@/components/portal/admin/AdminRequestsFilters.vue'
import AdminRequestsRow from '@/components/portal/admin/AdminRequestsRow.vue'
import PortalPagination from '@/components/portal/PortalPagination.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import RejectReasonModal from '@/components/portal/admin/RejectReasonModal.vue'
import { REQUEST_STATUS, REQUEST_SORT } from '@/constants/requests'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/admin-rich-row-stats.css'
import '@/assets/styles/portal/admin-rich-row.css'
import '@/assets/styles/portal/admin-rich-row-info.css'
import '@/assets/styles/portal/admin-rich-row-actions.css'

const { t } = useI18n()
const { showToast } = useToast()
const { requests, total, fetchAdminRequests, updateRequestStatus, deleteRequest } =
  usePortalRequests()
const { stats, fetchStats } = usePortalAdmin()
const { busyIds, rejectTarget, onAction, onRejectConfirm, cancelReject, onDelete } =
  useAdminRequestActions({ updateRequestStatus, deleteRequest, onStatusChanged, onDeleted })

const filter = ref('')
const typeFilter = ref('')
const sortKey = ref(REQUEST_SORT.RECENT)
const page = ref(1)
const perPage = ref(DEFAULT_PAGE_SIZE)
const loading = ref(false)

// Remembered across visits; it only applies to the all-statuses view, a
// status filter always shows what it names.
const HIDE_AVAILABLE_KEY = 'mk_admin_requests_hide_available'
const hideAvailable = ref(readHideAvailable())
const hidingAvailable = computed(() => !filter.value && hideAvailable.value)

function readHideAvailable() {
  try {
    return localStorage.getItem(HIDE_AVAILABLE_KEY) === '1'
  } catch {
    return false
  }
}

function setHideAvailable(value) {
  hideAvailable.value = value
  try {
    localStorage.setItem(HIDE_AVAILABLE_KEY, value ? '1' : '0')
  } catch {
    /* storage blocked (private mode): the choice lasts for this visit */
  }
  reload()
}

async function loadRequests() {
  loading.value = true
  try {
    await fetchAdminRequests({
      status: filter.value || null,
      page: page.value,
      perPage: perPage.value,
      sort: sortKey.value,
      mediaType: typeFilter.value || null,
      hideAvailable: hidingAvailable.value,
    })
  } catch (e) {
    console.error('[PortalRequests] load failed', e)
    showToast(t('common.apiError.loadFailed'), TOAST_TYPE.ERR)
  } finally {
    loading.value = false
  }
}

// Any status/type/sort/size change resets to the first page before reloading.
async function reload() {
  page.value = 1
  await loadRequests()
}

async function setFilter(value) {
  filter.value = value
  await reload()
}

function onTypeFilter(value) {
  typeFilter.value = value
  reload()
}

function onSortChange() {
  reload()
}

function onPage(p) {
  page.value = p
  loadRequests()
}

function onPerPage(size) {
  perPage.value = size
  reload()
}

// Keep the pager consistent after an in-place row removal (delete, or a
// status change that drops the row from an active filter): step back off an
// emptied page (and refetch a fresh total), otherwise decrement the total.
function afterRowRemoved() {
  if (!requests.value.length && page.value > 1) {
    page.value -= 1
    loadRequests()
  } else {
    total.value = Math.max(0, total.value - 1)
  }
}

function onStatusChanged(req, newStatus, reason) {
  // In-place update — a full list reload would flip `loading`, unmount
  // the list DOM and reset the viewport scroll to the top of the page.
  req.status = newStatus
  if (reason != null) req.reject_reason = reason
  const leavesView = filter.value
    ? newStatus !== filter.value
    : hidingAvailable.value && newStatus === REQUEST_STATUS.AVAILABLE
  if (leavesView) {
    requests.value = requests.value.filter(r => r.id !== req.id)
    afterRowRemoved()
  }
  fetchStats()
}

function onDeleted() {
  afterRowRemoved()
  fetchStats()
}

onMounted(() => {
  loadRequests()
  fetchStats()
})
</script>
