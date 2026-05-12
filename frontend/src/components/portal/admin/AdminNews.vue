<template>
  <div>
    <button class="pt-btn pt-btn--primary pt-btn--toolbar" @click="openCreate">
      <i class="icon-plus" />
      {{ $t('portal.admin.createNews') }}
    </button>

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
        <button class="pt-icon-btn" @click="remove(n.id)"><i class="icon-trash" /></button>
      </div>
      <div v-if="!news.length" class="pt-empty">{{ $t('common.noResults') }}</div>
    </div>

    <Teleport v-if="showForm" to="body">
      <div class="pt-popup-overlay" @click.self="closeForm">
        <div class="pt-popup pt-popup--md">
          <div class="pt-popup-header">
            <h2>{{ $t('portal.admin.createNews') }}</h2>
            <button
              class="pt-popup-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="closeForm"
            >
              <X :size="14" />
            </button>
          </div>
          <div class="pt-popup-body">
            <label>{{ $t('portal.news.titleLabel') }}</label>
            <input v-model="form.title" class="pt-input" maxlength="300" />
            <label>{{ $t('portal.news.content') }}</label>
            <textarea v-model="form.content" class="pt-input" rows="5" maxlength="10000" />
            <label>{{ $t('portal.news.typeLabel') }}</label>
            <select v-model="form.type" class="pt-input">
              <option v-for="type in types" :key="type" :value="type">
                {{ $t(`portal.news.types.${type}`) }}
              </option>
            </select>
            <label>{{ $t('portal.admin.news.startAtLabel') }}</label>
            <input v-model="form.start_at" type="datetime-local" class="pt-input" />
            <label>{{ $t('portal.admin.news.endAtLabel') }}</label>
            <input v-model="form.end_at" type="datetime-local" class="pt-input" />
          </div>
          <div class="pt-popup-footer">
            <button class="pt-btn pt-btn--primary" :disabled="!form.title.trim()" @click="submit">
              {{ $t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { usePortalNews } from '@/composables/portal/usePortalNews'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'

const { news, fetchNews, createNews, deleteNews } = usePortalNews()
const { showToast } = useToast()
const { t } = useI18n()

const showForm = ref(false)
const types = ['announcement', 'additions', 'maintenance', 'event', 'other']
const form = reactive({ title: '', content: '', type: 'announcement', start_at: '', end_at: '' })

function openCreate() {
  form.title = ''
  form.content = ''
  form.type = 'announcement'
  form.start_at = ''
  form.end_at = ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
}

function toIso(value) {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

function scheduleState(n) {
  const now = Date.now()
  const start = n.start_at ? Date.parse(n.start_at) : null
  const end = n.end_at ? Date.parse(n.end_at) : null
  if (start && start > now) return 'scheduled'
  if (end && end < now) return 'expired'
  return null
}

async function submit() {
  const payload = {
    title: form.title,
    content: form.content,
    type: form.type,
    start_at: toIso(form.start_at),
    end_at: toIso(form.end_at),
  }
  await createNews(payload)
  closeForm()
  showToast(t('common.saved'), TOAST_TYPE.OK)
  await fetchNews(true, { admin: true })
}

async function remove(id) {
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
  color: #fff;
}
.pt-btn--toolbar {
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
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.pt-icon-btn:hover {
  color: var(--portal-color-error);
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 1.5rem 0;
}
.pt-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgb(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.pt-popup {
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  width: 100%;
  display: flex;
  flex-direction: column;
}
.pt-popup--md {
  max-width: 500px;
}
.pt-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-popup-header h2 {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-popup-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: var(--portal-text-md);
  cursor: pointer;
}
.pt-popup-body {
  padding: 1rem 1.5rem;
}
.pt-popup-body label {
  display: block;
  font-size: var(--portal-text-sm);
  color: var(--text-muted);
  margin: 0.75rem 0 0.25rem;
}
.pt-input {
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--portal-text-sm);
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  text-align: right;
}
</style>
