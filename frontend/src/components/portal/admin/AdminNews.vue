<template>
  <div>
    <div class="pt-news-header">
      <button class="pt-btn pt-btn--primary" @click="openCreate">
        <i class="icon-plus" />
        {{ $t('portal.admin.createNews') }}
      </button>
    </div>

    <div class="pt-admin-table">
      <div v-for="n in news" :key="n.id" class="pt-news-row">
        <span class="pt-news-badge-mini" :class="`pt-badge--${n.type}`">{{ n.type }}</span>
        <span class="pt-news-title">{{ n.title }}</span>
        <span
          v-if="scheduleState(n) === 'scheduled'"
          class="pt-news-schedule pt-news-schedule--scheduled"
        >
          {{ $t('portal.admin.news.scheduledBadge') }}
        </span>
        <span
          v-else-if="scheduleState(n) === 'expired'"
          class="pt-news-schedule pt-news-schedule--expired"
        >
          {{ $t('portal.admin.news.expiredBadge') }}
        </span>
        <span class="pt-news-date">{{ new Date(n.created_at).toLocaleDateString() }}</span>
        <button
          class="pt-icon-btn pt-icon-btn--edit"
          type="button"
          :title="$t('portal.admin.news.editButton')"
          :aria-label="$t('portal.admin.news.editButton')"
          @click="openEdit(n)"
        >
          <Pencil :size="16" :stroke-width="2.5" />
        </button>
        <button
          class="pt-icon-btn pt-icon-btn--danger"
          type="button"
          :title="$t('portal.admin.news.deleteButton')"
          :aria-label="$t('portal.admin.news.deleteButton')"
          @click="remove(n.id)"
        >
          <Trash2 :size="16" :stroke-width="2.5" />
        </button>
      </div>
      <div v-if="!news.length" class="pt-empty">{{ $t('common.noResults') }}</div>
    </div>

    <AdminNewsForm
      v-if="showForm"
      :initial="editing"
      :editing-id="editingId"
      @close="closeForm"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePortalNews } from '@/composables/portal/usePortalNews'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { Pencil, Trash2 } from 'lucide-vue-next'
import AdminNewsForm from './AdminNewsForm.vue'

const { news, fetchNews, createNews, updateNews, deleteNews } = usePortalNews()
const { showToast } = useToast()
const confirm = useConfirm()
const { t } = useI18n()

const showForm = ref(false)
const editingId = ref(null)
const editing = ref(null)

function openCreate() {
  editingId.value = null
  editing.value = null
  showForm.value = true
}

function openEdit(n) {
  editingId.value = n.id
  editing.value = n
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingId.value = null
  editing.value = null
}

function scheduleState(n) {
  const now = Date.now()
  const start = n.start_at ? Date.parse(n.start_at) : null
  const end = n.end_at ? Date.parse(n.end_at) : null
  if (start && start > now) return 'scheduled'
  if (end && end < now) return 'expired'
  return null
}

async function onSubmit(payload) {
  if (editingId.value) {
    await updateNews(editingId.value, payload)
  } else {
    await createNews(payload)
  }
  closeForm()
  showToast(t('common.saved'), TOAST_TYPE.OK)
  await fetchNews(true, { admin: true })
}

async function remove(id) {
  const ok = await confirm({
    variant: 'danger',
    confirmLabel: t('common.delete'),
    message: t('portal.admin.news.confirmDelete'),
  })
  if (!ok) return
  await deleteNews(id)
  showToast(t('common.success'), TOAST_TYPE.OK)
  await fetchNews(true, { admin: true })
}

onMounted(() => fetchNews(true, { admin: true }))
</script>

<style scoped>
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-size: var(--portal-text-sm);
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.pt-btn--primary {
  background: var(--accent);
  color: var(--portal-text-primary);
}
.pt-news-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}
.pt-news-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-news-badge-mini {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  padding: 0.1rem 0.4rem;
  border-radius: var(--portal-radius-xs);
}
.pt-badge--announcement {
  background: rgb(var(--accent-rgb), 0.2);
  color: var(--accent);
}
.pt-badge--additions {
  background: rgb(var(--portal-color-success-rgb), 0.2);
  color: var(--portal-color-success);
}
.pt-badge--maintenance {
  background: rgb(234, 179, 8, 0.2);
  color: #eab308;
}
.pt-badge--event {
  background: rgb(var(--portal-color-premium-rgb), 0.2);
  color: var(--portal-color-premium);
}
.pt-badge--other {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}
.pt-news-title {
  flex: 1;
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
  font-size: var(--portal-text-base);
}
.pt-news-schedule {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  padding: 0.1rem 0.4rem;
  border-radius: var(--portal-radius-xs);
}
.pt-news-schedule--scheduled {
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
}
.pt-news-schedule--expired {
  background: var(--bg-tertiary);
  color: var(--text-faint);
}
.pt-news-date {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}
.pt-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--portal-radius-pill);
  color: var(--text-muted);
  cursor: pointer;
  box-shadow: var(--mk-pill-shadow-sm);
  transition:
    color var(--portal-dur-fast) ease,
    background var(--portal-dur-fast) ease;
}
@media (hover: hover) {
  .pt-icon-btn--edit:hover {
    color: var(--accent);
  }
  .pt-icon-btn--danger:hover {
    color: var(--portal-color-error);
  }
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 1.5rem 0;
}
</style>
