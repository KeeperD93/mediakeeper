<template>
  <section class="pt-gdpr-section">
    <header class="pt-gdpr-section-head">
      <div>
        <h3>{{ $t('portal.admin.settings.gdpr.title') }}</h3>
        <p class="pt-gdpr-section-desc">
          {{ $t('portal.admin.settings.gdpr.intro') }}
        </p>
      </div>
    </header>

    <div v-if="loading && !loaded" class="pt-gdpr-loading">
      {{ $t('common.loading') }}
    </div>

    <template v-else>
      <!-- Toggle: persists immediately. Class names are local to this
           component because the AdminSettings.vue ``pt-setting-*`` rules
           live in a parent ``<style scoped>`` block and would not bleed
           through Vue's data-v hashing. -->
      <div class="pt-gdpr-toggle-row">
        <div class="pt-gdpr-toggle-info">
          <span class="pt-gdpr-toggle-title">
            {{ $t('portal.admin.settings.gdpr.toggle.title') }}
          </span>
          <span class="pt-gdpr-toggle-desc">
            {{ $t('portal.admin.settings.gdpr.toggle.desc') }}
          </span>
        </div>
        <MkToggle
          :model-value="form.enabled"
          :disabled="saving"
          :aria-label="$t('portal.admin.settings.gdpr.toggle.title')"
          @update:model-value="onToggle"
        />
      </div>

      <!-- Config zone: visible only when the mode is on. The text
           editors / DPO / delay are still bound to ``form`` so toggling
           ON later picks up any preset edits. -->
      <div v-if="form.enabled" class="pt-gdpr-config">
        <div class="pt-gdpr-grid">
          <div v-if="currentLocale === 'fr'" class="pt-gdpr-field">
            <label class="pt-gdpr-label">
              {{ $t('portal.admin.settings.gdpr.privacyFr.title') }}
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.privacyFr.desc') }}
              </span>
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.privacyLangHint') }}
              </span>
            </label>
            <HelpEditor v-model="form.privacy_text_fr" />
          </div>

          <div v-if="currentLocale === 'en'" class="pt-gdpr-field">
            <label class="pt-gdpr-label">
              {{ $t('portal.admin.settings.gdpr.privacyEn.title') }}
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.privacyEn.desc') }}
              </span>
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.privacyLangHint') }}
              </span>
            </label>
            <HelpEditor v-model="form.privacy_text_en" />
          </div>
        </div>

        <div class="pt-gdpr-grid pt-gdpr-grid--inline">
          <div class="pt-gdpr-field">
            <label class="pt-gdpr-label">
              {{ $t('portal.admin.settings.gdpr.dpo.title') }}
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.dpo.desc') }}
              </span>
            </label>
            <input v-model="form.dpo_contact" type="text" class="pt-gdpr-input" maxlength="300" />
          </div>

          <div class="pt-gdpr-field pt-gdpr-field--narrow">
            <label class="pt-gdpr-label">
              {{ $t('portal.admin.settings.gdpr.delay.title') }}
              <span class="pt-gdpr-hint">
                {{ $t('portal.admin.settings.gdpr.delay.desc') }}
              </span>
            </label>
            <input
              v-model.number="form.account_purge_delay_days"
              type="number"
              class="pt-gdpr-input pt-gdpr-input--number"
              :min="DELAY_MIN"
              :max="DELAY_MAX"
            />
            <span v-if="delayInvalid" class="pt-gdpr-error">
              {{
                $t('portal.admin.settings.gdpr.delay.invalid', { min: DELAY_MIN, max: DELAY_MAX })
              }}
            </span>
          </div>
        </div>

        <div class="pt-gdpr-actions">
          <button
            type="button"
            class="pt-gdpr-save"
            :disabled="saving || delayInvalid"
            @click="onSave"
          >
            <Save :size="14" />
            <span>{{ $t('common.save') }}</span>
          </button>
          <span v-if="savedMessage" class="pt-gdpr-saved">{{ savedMessage }}</span>
        </div>

        <GdprPendingTable
          :rows="pending"
          :loading="pendingLoading"
          :cancelling-id="cancellingId"
          @refresh="loadPending"
          @cancel="onCancel"
        />
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save } from 'lucide-vue-next'
import HelpEditor from '@/components/portal/help/HelpEditor.vue'
import GdprPendingTable from '@/components/portal/admin/GdprPendingTable.vue'
import MkToggle from '@/components/common/MkToggle.vue'
import { DEFAULT_SETTINGS, useGdprAdmin } from '@/composables/portal/useGdprAdmin'

import '@/assets/styles/portal/admin-gdpr.css'

const DELAY_MIN = 7
const DELAY_MAX = 90
const SAVED_MESSAGE_TIMEOUT_MS = 2000

const { t, locale } = useI18n()
const { saving, fetchSettings, saveSettings, fetchPendingDeletions, cancelDeletionRequest } =
  useGdprAdmin()

const currentLocale = computed(() =>
  (locale.value || 'fr').toLowerCase().startsWith('en') ? 'en' : 'fr',
)

const form = reactive({ ...DEFAULT_SETTINGS })
const loading = ref(false)
const loaded = ref(false)
const savedMessage = ref('')
let savedTimer = null

const pending = ref([])
const pendingLoading = ref(false)
const cancellingId = ref(null)

const delayInvalid = computed(() => {
  const n = Number(form.account_purge_delay_days)
  return !Number.isFinite(n) || n < DELAY_MIN || n > DELAY_MAX
})

async function load() {
  loading.value = true
  try {
    const res = await fetchSettings()
    Object.assign(form, res)
    loaded.value = true
    if (form.enabled) await loadPending()
  } finally {
    loading.value = false
  }
}

async function loadPending() {
  pendingLoading.value = true
  try {
    pending.value = await fetchPendingDeletions()
  } finally {
    pendingLoading.value = false
  }
}

function flashSaved() {
  savedMessage.value = t('common.saved')
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => {
    savedMessage.value = ''
  }, SAVED_MESSAGE_TIMEOUT_MS)
}

async function onToggle(next) {
  form.enabled = next
  const res = await saveSettings({ enabled: next })
  Object.assign(form, res)
  flashSaved()
  if (next) await loadPending()
  else pending.value = []
}

async function onSave() {
  if (delayInvalid.value) return
  const res = await saveSettings({
    privacy_text_fr: form.privacy_text_fr,
    privacy_text_en: form.privacy_text_en,
    dpo_contact: form.dpo_contact,
    account_purge_delay_days: Number(form.account_purge_delay_days),
  })
  Object.assign(form, res)
  flashSaved()
}

async function onCancel(row) {
  cancellingId.value = row.id
  try {
    await cancelDeletionRequest(row.id)
    await loadPending()
  } finally {
    cancellingId.value = null
  }
}

onMounted(load)
</script>

<!-- Styles externalised to assets/styles/portal/admin-gdpr.css -->
