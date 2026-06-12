<template>
  <div class="arr-page">
    <header class="arr-head">
      <div>
        <h1 class="arr-title">
          <span class="arr-title-accent" aria-hidden="true" />
          {{ $t('portal.lists.title') }}
        </h1>
        <p class="arr-sub">{{ $t('portal.lists.subtitle') }}</p>
      </div>
      <button class="arr-create-btn" type="button" @click="openCreate">
        <Plus :size="16" :stroke-width="2.5" />
        {{ $t('portal.lists.createButton') }}
      </button>
    </header>

    <TabStrip
      v-model="activeTab"
      :tabs="listsTabs"
      placement="top"
      @update:model-value="switchTab"
    />

    <AdminListsTab v-if="activeTab === 'admin' && isAdmin" />

    <template v-else>
      <div v-if="loading" class="arr-loading"><MkSpinner size="md" /></div>

      <div v-else-if="!currentTabLists.length" class="arr-empty">
        <p class="arr-empty-text">
          {{ activeTab === 'mine' ? $t('portal.lists.emptyOwn') : $t('portal.lists.emptyPublic') }}
        </p>
        <button
          v-if="activeTab === 'mine'"
          class="arr-empty-cta"
          type="button"
          data-action="create-list"
          @click="openCreate"
        >
          <Plus :size="16" :stroke-width="2.5" />
          {{ $t('portal.lists.createFirst') }}
        </button>
      </div>

      <div v-else class="arr-list">
        <template v-for="(lst, idx) in currentTabLists" :key="lst.id">
          <ListRow
            :lst="lst"
            :index="idx + 1"
            :expanded="expandedId === lst.id"
            :export-url="svc.exportUrl"
            @toggle="toggleExpand"
            @edit="openEdit"
            @delete="remove"
            @copy-list="copy"
          />
          <ListExpansion
            v-if="expandedId === lst.id"
            :lst="lst"
            @remove-item="onRemoveItem(lst, $event)"
            @remove-contributor="onRemoveContributor(lst, $event)"
          />
        </template>
      </div>

      <PortalLoadMore :show="publicHasMore" :loading="loadingMorePublic" @load="loadMorePublic" />
    </template>

    <ListFormModal
      :open="formOpen"
      :initial="formInitial"
      :mode="formMode"
      @close="formOpen = false"
      @submit="onSubmitForm"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalLists } from '@/composables/portal/usePortalLists'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import ListFormModal from '@/components/portal/lists/ListFormModal.vue'
import ListRow from '@/components/portal/lists/ListRow.vue'
import ListExpansion from '@/components/portal/lists/ListExpansion.vue'
import AdminListsTab from '@/components/portal/lists/AdminListsTab.vue'
import TabStrip from '@/components/common/TabStrip.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import PortalLoadMore from '@/components/portal/PortalLoadMore.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { USER_ROLE } from '@/constants/auth'
import { Plus } from 'lucide-vue-next'

import '@/assets/styles/portal/admin-rich-row-header.css'
import '@/assets/styles/portal/admin-rich-row.css'
import '@/assets/styles/portal/admin-rich-row-actions.css'

const { t } = useI18n()
const { showToast } = useToast()
const svc = usePortalLists()
const mkConfirm = useConfirm()
const { profile } = usePortalAuth()

const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)
const activeTab = ref('mine')

const listsTabs = computed(() => {
  const tabs = [
    { id: 'mine', label: t('portal.lists.tabMine') },
    { id: 'public', label: t('portal.lists.tabPublic') },
  ]
  if (isAdmin.value) {
    tabs.push({ id: 'admin', label: t('portal.lists.tabAdmin') })
  }
  return tabs
})
const expandedId = ref(null)
const formOpen = ref(false)
const formMode = ref('create')
const formInitial = ref({})
const loading = ref(false)

const PUBLIC_PAGE = 50
const loadingMorePublic = ref(false)
const currentTabLists = computed(() =>
  activeTab.value === 'mine' ? svc.lists.value : svc.publicLists.value,
)
const publicHasMore = computed(() => activeTab.value === 'public' && svc.publicHasMore.value)

async function loadTab(tab) {
  loading.value = true
  try {
    if (tab === 'mine') await svc.fetchMyLists()
    else await svc.fetchPublicLists({ limit: PUBLIC_PAGE })
  } finally {
    loading.value = false
  }
}

async function loadMorePublic() {
  if (loadingMorePublic.value || !publicHasMore.value) return
  loadingMorePublic.value = true
  try {
    await svc.fetchPublicLists({
      limit: PUBLIC_PAGE,
      cursor: svc.publicCursor.value,
      append: true,
    })
  } finally {
    loadingMorePublic.value = false
  }
}

async function switchTab(tab) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  expandedId.value = null
  if (tab === 'admin') return
  await loadTab(tab)
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function openCreate() {
  formMode.value = 'create'
  formInitial.value = {}
  formOpen.value = true
}

function openEdit(lst) {
  formMode.value = 'edit'
  formInitial.value = {
    id: lst.id,
    name: lst.name,
    description: lst.description,
    privacy: lst.privacy,
    content_type: lst.content_type,
    genres: lst.genres || [],
  }
  formOpen.value = true
}

async function onSubmitForm(data) {
  const res =
    formMode.value === 'create'
      ? await svc.createList(data)
      : await svc.updateList(formInitial.value.id, data)
  if (res?.success) {
    formOpen.value = false
    showToast(t('common.success'), TOAST_TYPE.OK)
    await loadTab(activeTab.value)
  }
}

async function remove(lst) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('portal.lists.actions.confirmDelete'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  const res = await svc.deleteList(lst.id)
  if (res?.success) {
    expandedId.value = null
    await loadTab(activeTab.value)
  }
}

async function copy(lst) {
  const res = await svc.copyList(lst.id)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    if (activeTab.value === 'mine') await loadTab('mine')
  }
}

async function onRemoveItem(lst, itemId) {
  const res = await svc.removeItems(lst.id, { item_ids: [itemId] })
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await svc.fetchList(lst.id)
  }
}

async function onRemoveContributor(lst, userId) {
  const res = await svc.removeContributor(lst.id, userId)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await loadTab(activeTab.value)
  }
}

onMounted(() => loadTab('mine'))
</script>

<style scoped>
.arr-create-btn {
  padding: 10px 18px;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--portal-gradient-accent);
  color: var(--portal-text-primary);
  font-weight: var(--portal-font-extrabold);
  cursor: pointer;
  font-size: var(--portal-text-sm);
  letter-spacing: var(--portal-tracking-wide);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--portal-shadow-accent);
  -webkit-tap-highlight-color: transparent;
  transition:
    transform 0.18s,
    box-shadow 0.18s;
}
.arr-create-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--portal-shadow-accent-strong);
}

.arr-empty-text {
  margin: 0 0 1.25rem;
}
.arr-empty-cta {
  padding: 10px 18px;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--portal-gradient-accent);
  color: var(--portal-text-primary);
  font-weight: var(--portal-font-extrabold);
  cursor: pointer;
  font-size: var(--portal-text-sm);
  letter-spacing: var(--portal-tracking-wide);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--portal-shadow-accent);
  -webkit-tap-highlight-color: transparent;
  transition:
    transform 0.18s,
    box-shadow 0.18s;
}
@media (hover: hover) {
  .arr-empty-cta:hover {
    transform: translateY(-2px);
    box-shadow: var(--portal-shadow-accent-strong);
  }
}
.arr-empty-cta:active {
  transform: scale(0.97);
}
</style>
