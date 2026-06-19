<template>
  <SettingsSection
    :icon="Wrench"
    :title="$t('portal.admin.settings.cat.maintenance')"
    :description="$t('portal.admin.settings.cat.maintenanceDesc')"
  >
    <SettingRow
      :label="$t('portal.admin.settings.maintenance.title')"
      :description="$t('portal.admin.settings.maintenance.desc')"
    >
      <MkToggle
        :model-value="maintenance.enabled"
        :disabled="saving"
        :aria-label="$t('portal.admin.settings.maintenance.title')"
        @update:model-value="onToggle"
      />
    </SettingRow>

    <div v-if="maintenance.enabled" class="set-maint">
      <label class="set-maint-label" :for="textId">
        {{ $t('portal.admin.settings.maintenance.textLabel') }}
      </label>
      <textarea
        v-if="currentLocale === 'fr'"
        :id="textId"
        v-model="maintenance.text_fr"
        class="set-textarea"
        rows="3"
        maxlength="2000"
      />
      <textarea
        v-else
        :id="textId"
        v-model="maintenance.text_en"
        class="set-textarea"
        rows="3"
        maxlength="2000"
      />
      <div class="set-maint-actions">
        <button
          type="button"
          class="set-bar-btn set-bar-btn--primary"
          :disabled="saving"
          @click="saveText"
        >
          {{ $t('common.save') }}
        </button>
        <span v-if="savedMessage" class="set-maint-saved">{{ savedMessage }}</span>
      </div>
    </div>
  </SettingsSection>
</template>

<script setup>
import { computed, onMounted, reactive, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Wrench } from 'lucide-vue-next'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import MkToggle from '@/components/common/MkToggle.vue'
import SettingsSection from '../SettingsSection.vue'
import SettingRow from '../SettingRow.vue'

const MAINTENANCE_URL = '/api/portal/admin/maintenance'
const SAVED_MESSAGE_TIMEOUT_MS = 2000

const { t, locale } = useI18n()
const { apiGet, apiPatch } = useApi()
const { showToast } = useToast()
const textId = useId()

const maintenance = reactive({ enabled: false, text_fr: '', text_en: '' })
const saving = ref(false)
const savedMessage = ref('')
let savedTimer = null

const currentLocale = computed(() =>
  (locale.value || 'fr').toLowerCase().startsWith('en') ? 'en' : 'fr',
)

function flashSaved() {
  savedMessage.value = t('common.saved')
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => {
    savedMessage.value = ''
  }, SAVED_MESSAGE_TIMEOUT_MS)
}

async function onToggle(next) {
  saving.value = true
  try {
    const res = await apiPatch(MAINTENANCE_URL, { enabled: next })
    if (res) {
      Object.assign(maintenance, res)
      flashSaved()
    }
  } catch (e) {
    console.error('[SettingsMaintenance.onToggle]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}

async function saveText() {
  saving.value = true
  try {
    const payload =
      currentLocale.value === 'fr'
        ? { text_fr: maintenance.text_fr }
        : { text_en: maintenance.text_en }
    const res = await apiPatch(MAINTENANCE_URL, payload)
    if (res) {
      Object.assign(maintenance, res)
      flashSaved()
    }
  } catch (e) {
    console.error('[SettingsMaintenance.saveText]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await apiGet(MAINTENANCE_URL)
    if (res) Object.assign(maintenance, res)
  } catch (e) {
    console.error('[SettingsMaintenance.onMounted]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  }
})
</script>

<style scoped>
.set-maint {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1.25rem 1rem;
}
.set-maint-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.set-maint-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.set-maint-saved {
  font-size: var(--text-xs);
  color: var(--accent);
}
</style>
