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
        <span v-if="stats?.approved_total != null" class="arr-stat-total">
          {{ $t('portal.admin.req.statTotalSince', { count: stats.approved_total }) }}
        </span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="arr-toolbar">
      <div class="arr-pills">
        <button
          v-for="st in filters" :key="st.value"
          type="button"
          class="arr-pill"
          :class="{ 'arr-pill--active': filter === st.value }"
          @click="setFilter(st.value)"
        >{{ $t(st.label) }}</button>
        <span class="arr-pills-sep" aria-hidden="true" />
        <button
          v-for="tp in typeFilters" :key="tp.value || 'all'"
          type="button"
          class="arr-pill"
          :class="{ 'arr-pill--active': typeFilter === tp.value }"
          @click="typeFilter = tp.value"
        >{{ $t(tp.label) }}</button>
      </div>
      <select v-model="sortKey" class="arr-sort">
        <option value="recent">{{ $t('portal.admin.req.sortRecent') }}</option>
        <option value="oldest">{{ $t('portal.admin.req.sortOldest') }}</option>
        <option value="title">{{ $t('portal.admin.req.sortTitle') }}</option>
      </select>
    </div>

    <div v-if="loading" class="arr-loading"><MkSpinner size="md" /></div>

    <div v-else-if="!sortedRequests.length" class="arr-empty">
      {{ $t('common.noResults') }}
    </div>

    <div v-else class="arr-list">
      <AdminRequestsRow
        v-for="(req, idx) in sortedRequests"
        :key="req.id"
        :req="req"
        :index="idx + 1"
        @action="onAction(req, $event)"
        @delete="onDelete(req)"
      />
    </div>

    <RejectReasonModal
      :open="!!rejectTarget"
      :media-title="rejectTarget?.title || ''"
      @confirm="onRejectConfirm"
      @cancel="rejectTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalRequests } from '@/composables/portal/usePortalRequests'
import { usePortalAdmin } from '@/composables/portal/usePortalAdmin'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import AdminRequestsRow from '@/components/portal/admin/AdminRequestsRow.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import { useConfirm } from '@/composables/useConfirm'
import RejectReasonModal from '@/components/portal/admin/RejectReasonModal.vue'
import { REQUEST_STATUS } from '@/constants/requests'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/admin-rich-row.css'
import '@/assets/styles/portal/admin-rich-row-actions.css'

const { t } = useI18n()
const mkConfirm = useConfirm()
const { showToast } = useToast()
const { requests, fetchAdminRequests, updateRequestStatus, deleteRequest } = usePortalRequests()
const { stats, fetchStats } = usePortalAdmin()

const filter = ref('')
const typeFilter = ref('')
const sortKey = ref('recent')
const loading = ref(false)
const rejectTarget = ref(null)

const filters = [
  { value: '', label: 'portal.requests.allStatus' },
  { value: 'pending', label: 'portal.requests.pending' },
  { value: 'approved', label: 'portal.requests.approved' },
  { value: 'available', label: 'portal.requests.available' },
  { value: 'rejected', label: 'portal.requests.rejected' },
]

const typeFilters = [
  { value: '', label: 'portal.admin.req.typeAll' },
  { value: 'movie', label: 'portal.admin.req.typeMovies' },
  { value: 'tv', label: 'portal.admin.req.typeSeries' },
]

const sortedRequests = computed(() => {
  let list = [...requests.value]
  if (typeFilter.value) list = list.filter(r => r.media_type === typeFilter.value)
  switch (sortKey.value) {
    case 'oldest':
      return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    case 'title':
      return list.sort((a, b) => (a.title || '').localeCompare(b.title || ''))
    default:
      return list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  }
})

async function setFilter(value) {
  filter.value = value
  await load()
}

async function load() {
  loading.value = true
  try {
    await Promise.all([
      fetchAdminRequests(filter.value || null),
      fetchStats(),
    ])
  } finally {
    loading.value = false
  }
}

async function onAction(req, newStatus) {
  if (newStatus === REQUEST_STATUS.REJECTED) {
    rejectTarget.value = req
    return
  }
  await applyStatus(req, newStatus, null)
}

async function applyStatus(req, newStatus, reason) {
  const res = await updateRequestStatus(req.id, newStatus, reason)
  if (res?.success) {
    showToast(t('common.saved'), TOAST_TYPE.OK)
    // In-place update — a full list reload would flip `loading`, unmount
    // the list DOM and reset the viewport scroll to the top of the page.
    req.status = newStatus
    if (reason != null) req.reject_reason = reason
    if (filter.value && newStatus !== filter.value) {
      requests.value = requests.value.filter(r => r.id !== req.id)
    }
    fetchStats()
  }
}

async function onRejectConfirm(reason) {
  const req = rejectTarget.value
  rejectTarget.value = null
  if (!req) return
  await applyStatus(req, 'rejected', reason)
}

async function onDelete(req) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('portal.admin.req.confirmDelete'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  await deleteRequest(req.id)
  fetchStats()
}

onMounted(load)
</script>
