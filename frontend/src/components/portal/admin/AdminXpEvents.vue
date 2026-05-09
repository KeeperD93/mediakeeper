<template>
  <div>
    <div class="pt-xp-header">
      <p class="pt-xp-hint">{{ $t('portal.admin.xpEvents.hint') }}</p>
      <button class="pt-btn pt-btn--primary" @click="openCreate">
        + {{ $t('portal.admin.xpEvents.create') }}
      </button>
    </div>

    <div class="pt-admin-table">
      <XpEventRow
        v-for="ev in events"
        :key="ev.id"
        :ev="ev"
        :format-date="formatDate"
        @edit="openEdit"
        @remove="remove"
      />
      <div v-if="!events.length" class="pt-empty">{{ $t('portal.admin.xpEvents.empty') }}</div>
    </div>

    <XpEventForm
      v-if="showForm"
      v-model:form="form"
      v-model:selected-actions="selectedActions"
      :available-actions="availableActions"
      :can-save="canSave"
      :is-edit="!!editingId"
      @close="showForm = false"
      @submit="submit"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import XpEventRow from './AdminXpEvents/XpEventRow.vue'
import XpEventForm from './AdminXpEvents/XpEventForm.vue'

const mkConfirm = useConfirm()

const { apiGet, apiPost, apiPut, apiDelete } = useApi()
const { showToast } = useToast()
const { t } = useI18n()

const events = ref([])
const showForm = ref(false)
const editingId = ref(null)
const selectedActions = ref([])
const form = reactive({
  name: '',
  description: '',
  multiplier: 2.0,
  starts_at: '',
  ends_at: '',
  enabled: true,
})

const availableActions = [
  'achievement_unlocked',
  'watch_movie',
  'watch_episode',
  'complete_series',
  'daily_login',
  'request_created',
  'request_approved',
  'event_created',
  'event_joined',
  'streak_7',
  'streak_30',
]

const canSave = computed(
  () => form.name.trim() && form.starts_at && form.ends_at && form.multiplier > 0,
)

function formatDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function reset() {
  form.name = ''
  form.description = ''
  form.multiplier = 2.0
  form.starts_at = ''
  form.ends_at = ''
  form.enabled = true
  selectedActions.value = []
  editingId.value = null
}

function openCreate() {
  reset()
  // Default: tomorrow → 1 week later
  const now = new Date()
  const start = new Date(now.getTime() + 24 * 3600 * 1000)
  const end = new Date(start.getTime() + 7 * 24 * 3600 * 1000)
  form.starts_at = toLocalISO(start)
  form.ends_at = toLocalISO(end)
  showForm.value = true
}

function openEdit(ev) {
  editingId.value = ev.id
  form.name = ev.name
  form.description = ev.description || ''
  form.multiplier = ev.multiplier
  form.starts_at = toLocalISO(new Date(ev.starts_at))
  form.ends_at = toLocalISO(new Date(ev.ends_at))
  selectedActions.value = ev.action_filter
    ? ev.action_filter
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
    : []
  form.enabled = ev.enabled
  showForm.value = true
}

function toLocalISO(d) {
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d - tz).toISOString().slice(0, 16)
}

async function fetchEvents() {
  const r = await apiGet('/api/portal/admin/xp-events').catch(() => null)
  events.value = r?.items || []
}

async function submit() {
  const payload = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    multiplier: form.multiplier,
    starts_at: new Date(form.starts_at).toISOString(),
    ends_at: new Date(form.ends_at).toISOString(),
    action_filter: selectedActions.value.length ? selectedActions.value.join(',') : null,
    enabled: form.enabled,
  }
  try {
    if (editingId.value) {
      await apiPut(`/api/portal/admin/xp-events/${editingId.value}`, payload)
    } else {
      await apiPost('/api/portal/admin/xp-events', payload)
    }
    showToast(t('common.saved'), TOAST_TYPE.OK)
    showForm.value = false
    await fetchEvents()
  } catch (e) {
    console.error('[AdminXpEvents.save] failed to save xp event', e)
    showToast(t('common.apiError.saveFailed'), TOAST_TYPE.ERR)
  }
}

async function remove(id) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.delete'),
    message: t('portal.admin.xpEvents.confirmDelete'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  await apiDelete(`/api/portal/admin/xp-events/${id}`)
  showToast(t('common.success'), TOAST_TYPE.OK)
  await fetchEvents()
}

onMounted(fetchEvents)
</script>

<style scoped>
.pt-xp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.pt-xp-hint {
  font-size: var(--portal-text-sm);
  color: var(--text-muted);
  margin: 0;
  flex: 1;
  min-width: 200px;
}
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-size: var(--portal-text-sm);
}
.pt-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem 0;
  font-style: italic;
}
</style>
