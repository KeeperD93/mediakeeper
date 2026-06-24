<template>
  <div class="ru-page mk-page-root">
    <header class="ru-page-header">
      <div class="ru-page-heading">
        <h1 class="ru-page-title">{{ $t('requestsAdmin.users.title') }}</h1>
        <p class="ru-page-sub">{{ $t('requestsAdmin.users.subtitle') }}</p>
      </div>
      <div class="ru-page-actions">
        <button
          type="button"
          class="ru-btn ru-btn--ghost"
          :disabled="syncing"
          @click="onSyncEmbyIds"
        >
          <RefreshCw :size="16" />
          <span>
            {{
              syncing
                ? $t('requestsAdmin.users.actions.sync_emby_ids_running')
                : $t('requestsAdmin.users.actions.sync_emby_ids')
            }}
          </span>
        </button>
        <button type="button" class="ru-btn ru-btn--ghost" @click="openImport">
          <DownloadCloud :size="16" />
          <span>{{ $t('requestsAdmin.users.actions.import_emby') }}</span>
        </button>
        <button type="button" class="ru-btn ru-btn--primary" @click="openCreate">
          <UserPlus :size="16" />
          <span>{{ $t('requestsAdmin.users.actions.create_local') }}</span>
        </button>
      </div>
    </header>

    <RuStatsBanner :stats="stats" :active="bannerActive" @apply="onBannerApply" />

    <RuUsersToolbar
      v-model:search="filters.search"
      v-model:source="filters.source"
      v-model:role="filters.role"
      v-model:status="filters.status"
      v-model:tag="filters.tag"
      v-model:expires-within="filters.expires_within"
      v-model:include-deleted="filters.include_deleted"
      v-model:view-mode="viewMode"
      :tag-options="tagOptions"
      :total="total"
      :page="page"
      :per-page="perPage"
      :loading="loading"
      @update:page="onPage"
      @update:per-page="onPerPage"
    />

    <div v-if="loading && !items.length" class="ru-loading">{{ $t('common.loading') }}</div>

    <div v-else-if="!items.length" class="ru-empty">
      <Users :size="42" />
      <p>{{ $t('requestsAdmin.users.empty') }}</p>
    </div>

    <RuUsersTable
      v-else-if="viewMode === VIEW_MODE.TABLE"
      :items="items"
      :selected-ids="selectedIds"
      :active-id="drawerProfileId"
      :sort="filters.sort"
      :order="filters.order"
      @toggle="toggleSelection"
      @toggle-all="toggleAll"
      @open="openDrawer"
      @sort="onSortChange"
    />
    <RuUsersCards
      v-else
      :items="items"
      :selected-ids="selectedIds"
      :active-id="drawerProfileId"
      @toggle="toggleSelection"
      @open="openDrawer"
    />

    <RuBulkBar
      v-if="selectedIds.length"
      :count="selectedIds.length"
      @action="onBulkAction"
      @clear="selectedIds = []"
    />

    <RuUserDrawer
      :open="!!drawerProfileId"
      :profile-id="drawerProfileId"
      :ordered-ids="orderedIds"
      @close="closeDrawer"
      @changed="reload"
      @navigate="onDrawerNavigate"
    />

    <RuEmbyImportOverlay :open="importOpen" @close="importOpen = false" @imported="onImported" />

    <RuLocalCreateModal :open="createOpen" @close="createOpen = false" @created="onCreated" />
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DownloadCloud, RefreshCw, UserPlus, Users } from 'lucide-vue-next'

import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import { downloadJsonFile } from '@/composables/portal/useFileDownload'
import {
  BULK_ACTION,
  VIEW_MODE,
  STATUS_FILTER,
  EXPIRY_WARNING_DAYS,
} from '@/constants/portalAdminUsers'
import { DEFAULT_PAGE_SIZE } from '@/constants/pagination'

import RuUsersToolbar from './RuUsersToolbar.vue'
import RuUsersTable from './RuUsersTable.vue'
import RuUsersCards from './RuUsersCards.vue'
import RuBulkBar from './RuBulkBar.vue'
import RuUserDrawer from './RuUserDrawer.vue'
import RuEmbyImportOverlay from './RuEmbyImportOverlay.vue'
import RuLocalCreateModal from './RuLocalCreateModal.vue'
import RuStatsBanner from './RuStatsBanner.vue'

import '@/assets/styles/portal/admin-users.css'
import '@/assets/styles/portal/admin-users-toolbar.css'

const { t } = useI18n()
const { showToast } = useToast()
const confirm = useConfirm()
const api = usePortalAdminUsers()

const filters = reactive({
  search: '',
  source: '',
  role: '',
  status: '',
  tag: '',
  expires_within: null,
  include_deleted: false,
  sort: 'display_name',
  order: 'asc',
})

const viewMode = ref(VIEW_MODE.TABLE)

const items = ref([])
const total = ref(0)
const page = ref(1)
const perPage = ref(DEFAULT_PAGE_SIZE)
const loading = ref(false)
const selectedIds = ref([])

const drawerProfileId = ref(null)
const importOpen = ref(false)
const createOpen = ref(false)
const syncing = ref(false)
const stats = ref(null)
const tagOptions = ref([])

const bannerActive = computed(() => {
  if (filters.expires_within === EXPIRY_WARNING_DAYS) return 'expiring'
  if (filters.status === STATUS_FILTER.ACTIVE) return 'active'
  if (filters.status === STATUS_FILTER.INACTIVE) return 'inactive'
  if (filters.status === STATUS_FILTER.EXPIRED) return 'expired'
  return 'all'
})

const allIds = computed(() => items.value.map(u => u.id))
const orderedIds = computed(() => items.value.map(u => u.id))

let reloadTimer = null

async function reload() {
  loading.value = true
  try {
    const [res, freshStats] = await Promise.all([
      api.fetchUsers({
        search: filters.search || undefined,
        source: filters.source || undefined,
        role: filters.role || undefined,
        status: filters.status || undefined,
        tag: filters.tag || undefined,
        expires_within: filters.expires_within || undefined,
        include_deleted: filters.include_deleted || undefined,
        sort: filters.sort,
        order: filters.order,
        limit: perPage.value,
        offset: (page.value - 1) * perPage.value,
      }),
      api.fetchStats(),
    ])
    items.value = res?.items || []
    total.value = res?.total || 0
    if (freshStats) stats.value = freshStats
  } finally {
    loading.value = false
  }
  // Deletions can leave the current page past the end; clamp to the last
  // valid page so the admin never lands on a blank page behind the pager.
  const maxPage = Math.max(1, Math.ceil(total.value / perPage.value))
  if (page.value > maxPage) {
    page.value = maxPage
    await reload()
  }
}

async function reloadMeta() {
  const [s, t] = await Promise.all([api.fetchStats(), api.fetchTags()])
  stats.value = s || null
  tagOptions.value = t?.tags || []
}

function onBannerApply({ status, expires_within }) {
  filters.status = status
  filters.expires_within = expires_within
}

function onSortChange({ sort, order }) {
  filters.sort = sort
  filters.order = order
}

function debouncedReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(reload, 250)
}
// Selection is scoped to the visible page: drop it whenever the result set
// changes (filter/sort/search) or the page/size moves, so a bulk action can
// never run on rows that have scrolled off-screen.
watch(
  filters,
  () => {
    page.value = 1
    selectedIds.value = []
    debouncedReload()
  },
  { deep: true },
)

function onPage(p) {
  selectedIds.value = []
  page.value = p
  reload()
}
function onPerPage(size) {
  selectedIds.value = []
  perPage.value = size
  page.value = 1
  reload()
}

function toggleSelection(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}
function toggleAll() {
  if (selectedIds.value.length === allIds.value.length) selectedIds.value = []
  else selectedIds.value = [...allIds.value]
}
function openDrawer(profileId) {
  drawerProfileId.value = profileId
}
function closeDrawer() {
  drawerProfileId.value = null
}
function onDrawerNavigate(direction) {
  const idx = orderedIds.value.indexOf(drawerProfileId.value)
  if (idx < 0) return
  const next = direction === 'prev' ? idx - 1 : idx + 1
  if (next >= 0 && next < orderedIds.value.length) drawerProfileId.value = orderedIds.value[next]
}
function openImport() {
  importOpen.value = true
}
function openCreate() {
  createOpen.value = true
}

async function onSyncEmbyIds() {
  syncing.value = true
  try {
    const res = await api.syncEmbyIds()
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(
      t('requestsAdmin.users.toasts.embyIdsSynced', {
        updated: res?.updated || 0,
        already: res?.already_linked || 0,
        unmatched: res?.unmatched || 0,
      }),
      TOAST_TYPE.OK,
    )
    await reload()
  } finally {
    syncing.value = false
  }
}

async function onBulkAction({ action, payload = null }) {
  if (action === BULK_ACTION.DELETE) {
    const ok = await confirm({
      title: t('requestsAdmin.users.confirms.bulkDeleteTitle'),
      message: t('requestsAdmin.users.confirms.bulkDelete', { count: selectedIds.value.length }),
      variant: 'danger',
      confirmLabel: t('common.delete'),
    })
    if (!ok) return
  }
  if (action === BULK_ACTION.EXPORT) {
    for (const id of selectedIds.value) {
      try {
        const data = await api.exportUser(id)
        downloadJsonFile(data, `mk-user-${id}.json`)
      } catch {
        /* per-user failure already toasted by useApi */
      }
    }
    showToast(t('requestsAdmin.users.toasts.exported'), TOAST_TYPE.OK)
    return
  }
  // The "bulk edit" overlay carries two groups; fan out to the matching
  // backend actions and report the real applied count once both have run.
  if (action === BULK_ACTION.BULK_EDIT) {
    const ids = [...selectedIds.value]
    const { permissions = {}, quota = {} } = payload || {}
    const groups = [
      Object.keys(permissions).length && {
        action: BULK_ACTION.SET_PERMISSIONS,
        payload: { permissions },
      },
      Object.keys(quota).length && { action: BULK_ACTION.SET_QUOTA, payload: quota },
    ].filter(Boolean)
    if (!groups.length) return
    let applied = 0
    for (const g of groups) {
      const r = await api.bulkAction({ action: g.action, profile_ids: ids, payload: g.payload })
      if (r?.ok) applied += r.processed || 0
    }
    if (applied > 0) {
      showToast(t('requestsAdmin.users.toasts.bulkDone', { count: applied }), TOAST_TYPE.OK)
      selectedIds.value = []
      await reload()
    } else {
      // Every target was rejected (e.g. an inverted auto band); keep the
      // selection so the admin can fix the values and retry.
      showToast(t('requestsAdmin.users.toasts.bulkNoChange'), TOAST_TYPE.ERR)
    }
    return
  }
  const res = await api.bulkAction({
    action,
    profile_ids: [...selectedIds.value],
    payload,
  })
  if (res?.ok) {
    showToast(t('requestsAdmin.users.toasts.bulkDone', { count: res.processed }), TOAST_TYPE.OK)
    selectedIds.value = []
    await reload()
  }
}

async function onImported(summary) {
  importOpen.value = false
  showToast(
    t('requestsAdmin.users.toasts.imported', { created: summary?.created || 0 }),
    TOAST_TYPE.OK,
  )
  await reload()
}
async function onCreated() {
  createOpen.value = false
  showToast(t('requestsAdmin.users.toasts.created'), TOAST_TYPE.OK)
  await reload()
}
onMounted(async () => {
  await Promise.all([reload(), reloadMeta()])
})
</script>

<style scoped>
.ru-pager-bar {
  display: flex;
  justify-content: flex-end;
  margin: 0.75rem 0;
}
</style>
