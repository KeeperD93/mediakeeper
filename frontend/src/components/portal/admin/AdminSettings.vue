<template>
  <div class="pt-admin-settings">
    <div v-if="loading && !loaded" class="pt-settings-loading">
      {{ $t('common.loading') }}
    </div>

    <div v-else class="pt-settings-list">
      <!-- Anonymisation des demandes -->
      <label class="pt-setting-row">
        <div class="pt-setting-info">
          <span class="pt-setting-title">
            {{ $t('portal.admin.settings.anonymizeRequests.title') }}
          </span>
          <span class="pt-setting-desc">
            {{ $t('portal.admin.settings.anonymizeRequests.desc') }}
          </span>
        </div>
        <input
          type="checkbox"
          class="pt-setting-toggle"
          :checked="settings.anonymize_requests"
          :disabled="saving"
          @change="update('anonymize_requests', $event.target.checked)"
        />
      </label>

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

      <p v-if="savedMessage" class="pt-settings-saved">{{ savedMessage }}</p>

      <GdprSection />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import GdprSection from '@/components/portal/admin/GdprSection.vue'

const { t } = useI18n()
const { apiGet, apiPatch } = useApi()

const settings = ref({ anonymize_requests: false, hero_trend_count: 10 })
const loading = ref(false)
const loaded = ref(false)
const saving = ref(false)
const savedMessage = ref('')

async function fetchSettings() {
  loading.value = true
  try {
    const res = await apiGet('/api/portal/admin/settings')
    if (res) {
      settings.value = { ...settings.value, ...res }
      loaded.value = true
    }
  } finally {
    loading.value = false
  }
}

let savedTimer = null
async function update(key, value) {
  saving.value = true
  try {
    const res = await apiPatch('/api/portal/admin/settings', { [key]: value })
    if (res) {
      settings.value = { ...settings.value, ...res }
      savedMessage.value = t('common.saved')
      if (savedTimer) clearTimeout(savedTimer)
      savedTimer = setTimeout(() => {
        savedMessage.value = ''
      }, 2000)
    }
  } finally {
    saving.value = false
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
  font-size: var(--portal-text-sm);
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
    border-color var(--portal-dur-fast),
    background var(--portal-dur-fast);
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
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}
.pt-setting-desc {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
  line-height: 1.35;
}
.pt-setting-toggle {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
  cursor: pointer;
}
.pt-setting-number {
  flex-shrink: 0;
  width: 60px;
  padding: 0.35rem 0.5rem;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-medium);
  text-align: center;
  cursor: pointer;
}
.pt-setting-number:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-settings-saved {
  font-size: var(--portal-text-xs);
  color: var(--accent);
  margin-top: 0.5rem;
  padding-left: 0.25rem;
}
</style>
