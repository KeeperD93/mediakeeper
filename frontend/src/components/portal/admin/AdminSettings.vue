<template>
  <div class="pt-admin-settings">
    <div v-if="loading && !loaded" class="pt-settings-loading">
      {{ $t('common.loading') }}
    </div>

    <div v-else class="pt-settings-list">
      <!-- Anonymisation des demandes -->
      <div class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.anonymizeRequests.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.anonymizeRequests.desc') }}
          </span>
        </div>
        <MkToggle
          :model-value="settings.anonymize_requests"
          :disabled="saving"
          :aria-label="$t('portal.admin.settings.anonymizeRequests.title')"
          @update:model-value="v => update('anonymize_requests', v)"
        />
      </div>

      <!-- Allow adult content requests -->
      <div class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.allowAdultRequests.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.allowAdultRequests.desc') }}
          </span>
        </div>
        <MkToggle
          :model-value="settings.allow_adult_requests"
          :disabled="saving"
          :aria-label="$t('portal.admin.settings.allowAdultRequests.title')"
          @update:model-value="v => update('allow_adult_requests', v)"
        />
      </div>

      <!-- Number of trends in the hero -->
      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.heroTrendCount.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.heroTrendCount.desc') }}
          </span>
        </div>
        <input
          type="number"
          class="pt-setting-number"
          min="0"
          max="20"
          :value="settings.hero_trend_count"
          :disabled="saving"
          @change="update('hero_trend_count', parseInt($event.target.value) || 0)"
        />
      </label>

      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.requestsCleanup.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.requestsCleanup.desc') }}
          </span>
        </div>
        <input
          type="number"
          class="pt-setting-number"
          min="0"
          max="365"
          :value="settings['requests.auto_cleanup_days']"
          :disabled="saving"
          @change="update('requests.auto_cleanup_days', parseInt($event.target.value) || 0)"
        />
      </label>

      <!-- Event capacity bounds — step-5 select pair. The service-layer
           snaps any out-of-step value and re-orders ``min > max`` so the
           selects below stay in sync with whatever the backend accepts. -->
      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.eventCapacityMin.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.eventCapacityMin.desc') }}
          </span>
        </div>
        <select
          class="pt-setting-select"
          :value="settings['events.max_participants_min']"
          :disabled="saving"
          @change="update('events.max_participants_min', parseInt($event.target.value))"
        >
          <option v-for="v in CAPACITY_OPTIONS" :key="`min-${v}`" :value="v">
            {{ v }}
          </option>
        </select>
      </label>

      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.eventCapacityMax.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.eventCapacityMax.desc') }}
          </span>
        </div>
        <select
          class="pt-setting-select"
          :value="settings['events.max_participants_max']"
          :disabled="saving"
          @change="update('events.max_participants_max', parseInt($event.target.value))"
        >
          <option v-for="v in CAPACITY_OPTIONS" :key="`max-${v}`" :value="v">
            {{ v }}
          </option>
        </select>
      </label>

      <!-- Default portal language for users who have not picked one -->
      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.defaultLanguage.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.defaultLanguage.desc') }}
          </span>
        </div>
        <select
          class="pt-setting-select"
          :value="settings.default_language"
          :disabled="saving"
          @change="update('default_language', $event.target.value)"
        >
          <option value="">{{ $t('portal.admin.settings.defaultLanguage.auto') }}</option>
          <option v-for="loc in AVAILABLE_LOCALES" :key="loc.code" :value="loc.code">
            {{ loc.label }}
          </option>
        </select>
      </label>

      <!-- Maintenance mode toggle -->
      <div class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.maintenance.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.maintenance.desc') }}
          </span>
        </div>
        <MkToggle
          :model-value="maintenance.enabled"
          :disabled="maintSaving"
          :aria-label="$t('portal.admin.settings.maintenance.title')"
          @update:model-value="toggleMaintenance"
        />
      </div>

      <!-- Maintenance text editor — locale-scoped, only when ON -->
      <div v-if="maintenance.enabled" class="pt-maint-editor">
        <label class="pt-maint-label">
          {{ $t('portal.admin.settings.maintenance.textLabel') }}
        </label>
        <textarea
          v-if="currentLocale === 'fr'"
          v-model="maintenance.text_fr"
          class="pt-maint-textarea"
          rows="3"
          maxlength="2000"
        />
        <textarea
          v-else
          v-model="maintenance.text_en"
          class="pt-maint-textarea"
          rows="3"
          maxlength="2000"
        />
        <div class="pt-maint-actions">
          <button
            type="button"
            class="pt-btn pt-btn--primary"
            :disabled="maintSaving"
            @click="saveMaintenanceText"
          >
            {{ $t('common.save') }}
          </button>
        </div>
      </div>

      <p v-if="savedMessage" class="pt-settings-saved">{{ savedMessage }}</p>

      <GdprSection />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { AVAILABLE_LOCALES } from '@/i18n'
import { useApi } from '@/composables/useApi'
import GdprSection from '@/components/portal/admin/GdprSection.vue'
import MkToggle from '@/components/common/MkToggle.vue'

const { t, locale } = useI18n()
const { apiGet, apiPatch } = useApi()

// Step-5 options for the per-event capacity selects (matches the
// backend ``PORTAL_EVENT_CAPACITY_STEP``). The select pair shows
// the same options for both min and max — the service layer snaps
// and re-orders if the admin picks ``min > max``.
const CAPACITY_OPTIONS = [5, 10, 15, 20]

const settings = ref({
  anonymize_requests: false,
  allow_adult_requests: false,
  hero_trend_count: 10,
  'requests.auto_cleanup_days': 0,
  'events.max_participants_min': 5,
  'events.max_participants_max': 20,
  default_language: '',
})
const maintenance = reactive({ enabled: false, text_fr: '', text_en: '' })
const loading = ref(false)
const loaded = ref(false)
const saving = ref(false)
const maintSaving = ref(false)
const savedMessage = ref('')

const currentLocale = computed(() =>
  (locale.value || 'fr').toLowerCase().startsWith('en') ? 'en' : 'fr',
)

async function fetchSettings() {
  loading.value = true
  try {
    const [res, maint] = await Promise.all([
      apiGet('/api/portal/admin/settings'),
      apiGet('/api/portal/admin/maintenance'),
    ])
    if (res) settings.value = { ...settings.value, ...res }
    if (maint) Object.assign(maintenance, maint)
    loaded.value = true
  } finally {
    loading.value = false
  }
}

let savedTimer = null
function flashSaved() {
  savedMessage.value = t('common.saved')
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => {
    savedMessage.value = ''
  }, 2000)
}

async function update(key, value) {
  saving.value = true
  try {
    const res = await apiPatch('/api/portal/admin/settings', { [key]: value })
    if (res) {
      settings.value = { ...settings.value, ...res }
      flashSaved()
    }
  } finally {
    saving.value = false
  }
}

async function toggleMaintenance(next) {
  maintSaving.value = true
  try {
    const res = await apiPatch('/api/portal/admin/maintenance', { enabled: next })
    if (res) {
      Object.assign(maintenance, res)
      flashSaved()
    }
  } finally {
    maintSaving.value = false
  }
}

async function saveMaintenanceText() {
  maintSaving.value = true
  try {
    const payload =
      currentLocale.value === 'fr'
        ? { text_fr: maintenance.text_fr }
        : { text_en: maintenance.text_en }
    const res = await apiPatch('/api/portal/admin/maintenance', payload)
    if (res) {
      Object.assign(maintenance, res)
      flashSaved()
    }
  } finally {
    maintSaving.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
.pt-admin-settings {
  max-width: 720px;
}
.pt-settings-loading {
  padding: 1rem;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.pt-settings-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.pt-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  cursor: pointer;
  transition:
    border-color var(--duration-fast),
    background var(--duration-fast);
}
.pt-setting-row:hover {
  border-color: var(--border-hover);
}
.pt-setting-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}
.pt-setting-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.pt-setting-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.35;
}
.pt-setting-number {
  flex-shrink: 0;
  width: 60px;
  padding: 0.35rem 0.5rem;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-align: center;
  cursor: pointer;
}
.pt-setting-number:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-setting-select {
  flex-shrink: 0;
  min-width: 96px;
  padding: 0.4rem 0.7rem;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}
.pt-setting-select:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-settings-saved {
  font-size: var(--text-xs);
  color: var(--accent);
  margin-top: 0.5rem;
  padding-left: 0.25rem;
}
.pt-maint-editor {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.pt-maint-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.pt-maint-textarea {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--text-sm);
  font-family: inherit;
  resize: vertical;
}
.pt-maint-textarea:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-maint-actions {
  display: flex;
  justify-content: flex-end;
}
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--font-medium);
  cursor: pointer;
  font-size: var(--text-sm);
}
.pt-btn--primary {
  background: var(--accent);
  color: var(--text-primary);
}
.pt-btn--primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
