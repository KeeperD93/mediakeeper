<template>
  <div class="adm-lists">
    <h3 class="adm-lists-title">{{ $t('portal.lists.admin.title') }}</h3>
    <p class="adm-lists-sub">{{ $t('portal.lists.subtitle') }}</p>

    <div v-if="loading" class="adm-loading">
      <MkSpinner size="md" />
    </div>

    <div v-else-if="!allLists.length" class="adm-empty">
      {{ $t('portal.lists.emptyPublic') }}
    </div>

    <table v-else class="adm-table mk-table">
      <thead>
        <tr>
          <th>{{ $t('portal.lists.form.name') }}</th>
          <th>{{ $t('portal.lists.form.privacyLabel') }}</th>
          <th>{{ $t('portal.lists.itemCount', { count: 0 }, 2) }}</th>
          <th>{{ $t('common.actions') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="lst in allLists" :key="lst.id" :class="{ 'adm-row--deleted': lst.is_deleted }">
          <td :data-label="$t('portal.lists.form.name')">
            <span class="adm-name">{{ lst.name }}</span>
            <span v-if="lst.owner_muted" class="adm-muted-tag">🔇</span>
          </td>
          <td :data-label="$t('portal.lists.form.privacyLabel')">
            <span class="adm-privacy" :class="`adm-privacy--${lst.privacy}`">
              {{ $t(`portal.lists.privacy.${lst.privacy}`) }}
            </span>
          </td>
          <td :data-label="$t('portal.lists.itemCount', { count: 0 }, 2)">
            {{ lst.item_count }}
          </td>
          <td :data-label="$t('common.actions')" class="adm-actions">
            <button v-if="lst.is_deleted" type="button" class="adm-btn" @click="undelete(lst.id)">
              {{ $t('portal.lists.admin.undelete') }}
            </button>
            <button type="button" class="adm-btn" @click="toggleMute(lst)">
              {{
                lst.owner_muted
                  ? $t('portal.lists.admin.unmuteOwner')
                  : $t('portal.lists.admin.muteOwner')
              }}
            </button>
            <button type="button" class="adm-btn adm-btn--danger" @click="hardDelete(lst.id)">
              {{ $t('portal.lists.admin.hardDelete') }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <PortalLoadMore :show="hasMore" :loading="loadingMore" @load="loadMore" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalLists } from '@/composables/portal/usePortalLists'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import MkSpinner from '@/components/common/MkSpinner.vue'
import PortalLoadMore from '@/components/portal/PortalLoadMore.vue'
import { useConfirm } from '@/composables/useConfirm'

const { t } = useI18n()
const { showToast } = useToast()
const svc = usePortalLists()
const mkConfirm = useConfirm()
const loading = ref(false)

const MOD_PAGE = 50
const allLists = computed(() => svc.moderationLists.value)
const loadingMore = ref(false)
const hasMore = computed(() => svc.moderationHasMore.value)

async function load() {
  loading.value = true
  try {
    await svc.fetchModerationLists({ limit: MOD_PAGE })
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    await svc.fetchModerationLists({
      limit: MOD_PAGE,
      cursor: svc.moderationCursor.value,
      append: true,
    })
  } finally {
    loadingMore.value = false
  }
}

async function undelete(id) {
  const res = await svc.adminUndelete(id)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await load()
  }
}

async function hardDelete(id) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('portal.lists.actions.confirmDelete'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  const res = await svc.adminHardDelete(id)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await load()
  }
}

async function toggleMute(lst) {
  const res = await svc.adminMuteOwner(lst.id, !lst.owner_muted)
  if (res?.success) {
    showToast(t('common.success'), TOAST_TYPE.OK)
    await load()
  }
}

onMounted(load)
</script>

<style scoped>
.adm-lists {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.adm-lists-title {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin: 0;
}
.adm-lists-sub {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
  margin: 0 0 12px;
}
.adm-loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}
.adm-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
  font-size: var(--portal-text-sm);
}

.adm-table {
  width: 100%;
  border-collapse: collapse;
}
.adm-table th {
  text-align: left;
  padding: 8px 10px;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  border-bottom: 1px solid var(--portal-border-default);
}
.adm-table td {
  padding: 10px;
  font-size: var(--portal-text-sm);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--portal-border-faint);
}
.adm-row--deleted {
  opacity: 0.55;
}
.adm-name {
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
  margin-right: 6px;
}
.adm-muted-tag {
  font-size: var(--portal-text-sm);
}

.adm-privacy {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.adm-privacy--private {
  background: rgb(156, 163, 175, 0.18);
  color: #d1d5db;
}
.adm-privacy--public_readonly {
  background: rgb(var(--portal-color-info-rgb), 0.18);
  color: var(--portal-color-info-soft);
}
.adm-privacy--collaborative {
  background: rgb(var(--portal-color-premium-rgb), 0.18);
  color: var(--portal-color-premium-soft);
}

.adm-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.adm-btn {
  padding: 6px 10px;
  min-height: 34px;
  border-radius: var(--radius-btn);
  border: 1px solid rgb(255, 255, 255, 0.1);
  background: rgb(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .adm-btn:hover {
    border-color: var(--portal-text-disabled);
    color: var(--text-primary);
  }
}
.adm-btn--danger {
  color: var(--portal-color-error-soft);
  border-color: rgb(var(--portal-color-error-rgb), 0.25);
}
@media (hover: hover) {
  .adm-btn--danger:hover {
    background: rgb(var(--portal-color-error-rgb), 0.14);
  }
}
</style>
