<template>
  <div>
    <div class="pt-xp-header">
      <p class="pt-xp-hint">{{ $t('portal.admin.xpEvents.hint') }}</p>
      <button class="pt-btn pt-btn--primary" @click="openCreate">
        + {{ $t('portal.admin.xpEvents.create') }}
      </button>
    </div>

    <div class="pt-admin-table">
      <div
        v-for="ev in events"
        :key="ev.id"
        class="pt-xp-row"
        :class="{ 'pt-xp-row--active': ev.is_active }"
      >
        <span
          class="pt-xp-status"
          :class="{ 'pt-xp-status--on': ev.is_active }"
          :title="
            ev.is_active
              ? $t('portal.admin.xpEvents.active')
              : ev.enabled
                ? $t('portal.admin.xpEvents.scheduled')
                : $t('portal.admin.xpEvents.disabled')
          "
        >
          ●
        </span>
        <span class="pt-xp-mult">×{{ ev.multiplier }}</span>
        <div class="pt-xp-info">
          <div class="pt-xp-name">{{ ev.name }}</div>
          <div class="pt-xp-dates">
            {{ formatDate(ev.starts_at) }} → {{ formatDate(ev.ends_at) }}
          </div>
          <div v-if="ev.action_filter" class="pt-xp-filters">
            <span
              v-for="a in ev.action_filter
                .split(',')
                .map(s => s.trim())
                .filter(Boolean)"
              :key="a"
              class="pt-xp-filter"
            >
              {{ $t(`portal.admin.xpEvents.actions.${a}`, a) }}
            </span>
          </div>
        </div>
        <button class="pt-icon-btn" :title="$t('common.edit')" @click="openEdit(ev)">✎</button>
        <button
          class="pt-icon-btn pt-icon-btn--danger"
          :title="$t('common.delete')"
          @click="remove(ev.id)"
        >
          <Trash2 :size="14" />
        </button>
      </div>
      <div v-if="!events.length" class="pt-empty">{{ $t('portal.admin.xpEvents.empty') }}</div>
    </div>

    <Teleport v-if="showForm" to="body">
      <div class="pt-popup-overlay" @click.self="showForm = false">
        <div class="pt-popup">
          <div class="pt-popup-header">
            <h2>
              {{
                editingId
                  ? $t('portal.admin.xpEvents.editTitle')
                  : $t('portal.admin.xpEvents.createTitle')
              }}
            </h2>
            <button
              class="pt-popup-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="showForm = false"
            >
              <X :size="14" />
            </button>
          </div>
          <div class="pt-popup-body">
            <label>{{ $t('portal.admin.xpEvents.name') }}</label>
            <input
              v-model="form.name"
              class="pt-input"
              maxlength="100"
              :placeholder="$t('portal.admin.xpEvents.namePlaceholder')"
            />

            <label>{{ $t('portal.admin.xpEvents.description') }}</label>
            <textarea v-model="form.description" class="pt-input" rows="2" maxlength="500" />

            <div class="pt-row-2">
              <div>
                <label>{{ $t('portal.admin.xpEvents.multiplier') }}</label>
                <input
                  v-model.number="form.multiplier"
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="20"
                  class="pt-input"
                />
              </div>
              <div>
                <label>{{ $t('portal.admin.xpEvents.actionFilter') }}</label>
                <div class="pt-action-filter">
                  <label class="pt-action-row pt-action-row--all">
                    <input
                      type="checkbox"
                      :checked="!selectedActions.length"
                      @change="selectedActions = []"
                    />
                    <strong>{{ $t('portal.admin.xpEvents.allActions') }}</strong>
                  </label>
                  <label v-for="a in availableActions" :key="a" class="pt-action-row">
                    <input v-model="selectedActions" type="checkbox" :value="a" />
                    <span>{{ $t(`portal.admin.xpEvents.actions.${a}`) }}</span>
                    <code class="pt-action-code">{{ a }}</code>
                  </label>
                </div>
              </div>
            </div>

            <div class="pt-row-2">
              <div>
                <label>{{ $t('portal.admin.xpEvents.startsAt') }}</label>
                <input v-model="form.starts_at" type="datetime-local" class="pt-input" />
              </div>
              <div>
                <label>{{ $t('portal.admin.xpEvents.endsAt') }}</label>
                <input v-model="form.ends_at" type="datetime-local" class="pt-input" />
              </div>
            </div>

            <label class="pt-checkbox">
              <input v-model="form.enabled" type="checkbox" />
              {{ $t('portal.admin.xpEvents.enabled') }}
            </label>
          </div>
          <div class="pt-popup-footer">
            <button class="pt-btn" @click="showForm = false">{{ $t('common.cancel') }}</button>
            <button class="pt-btn pt-btn--primary" :disabled="!canSave" @click="submit">
              {{ $t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { Trash2, X } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

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
.pt-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pt-xp-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-xp-row--active {
  background: rgb(var(--accent-rgb), 0.06);
}
.pt-xp-status {
  font-size: var(--portal-text-md);
  color: var(--text-muted);
}
.pt-xp-status--on {
  color: var(--portal-color-success);
  text-shadow: 0 0 6px rgb(var(--portal-color-success-rgb), 0.5);
}
.pt-xp-mult {
  font-weight: var(--portal-font-extrabold);
  font-size: var(--portal-text-base);
  color: var(--accent);
  font-family: var(--portal-font-display);
  min-width: 40px;
}
.pt-xp-info {
  min-width: 0;
}
.pt-xp-name {
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  font-size: var(--portal-text-base);
}
.pt-xp-dates {
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.pt-xp-filters {
  grid-column: 3;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.25rem;
}
.pt-xp-filter {
  background: rgb(var(--accent-rgb), 0.12);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: var(--portal-radius-xs);
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-medium);
}

.pt-action-filter {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-tertiary);
  padding: 0.4rem 0.5rem;
}
.pt-action-row {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.4rem;
  border-radius: var(--portal-radius-xs);
  cursor: pointer;
  font-size: var(--portal-text-sm) !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
}
.pt-action-row:hover {
  background: rgb(var(--accent-rgb), 0.08);
}
.pt-action-row--all {
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.25rem !important;
  padding-bottom: 0.4rem;
}
.pt-action-row input[type='checkbox'] {
  margin: 0;
  cursor: pointer;
  flex-shrink: 0;
}
.pt-action-row span {
  flex: 1;
}
.pt-action-code {
  font-family: var(--portal-font-mono);
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 1px 5px;
  border-radius: 3px;
}
.pt-icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--portal-text-md);
  padding: 0.25rem 0.5rem;
  border-radius: var(--portal-radius-xs);
}
.pt-icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.pt-icon-btn--danger:hover {
  color: var(--portal-color-error);
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem 0;
  font-style: italic;
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
  max-width: 560px;
  display: flex;
  flex-direction: column;
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
  max-height: 70vh;
  overflow-y: auto;
}
.pt-popup-body label {
  display: block;
  font-size: var(--portal-text-sm);
  color: var(--text-muted);
  margin: 0.75rem 0 0.25rem;
}
.pt-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--portal-text-sm);
}
.pt-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.pt-checkbox {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  cursor: pointer;
  color: var(--text-primary) !important;
  font-size: var(--portal-text-sm) !important;
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
