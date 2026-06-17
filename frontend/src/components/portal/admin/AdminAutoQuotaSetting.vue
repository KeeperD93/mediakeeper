<template>
  <section class="pt-aq-section">
    <!-- Self-contained card (same pattern as AdminDonationSetting): reads and
         writes the quota.auto.* instance settings through /admin/settings.
         Class names are local so the parent's pt-setting-* scoped rules
         don't bleed through Vue's hashing. -->
    <div class="pt-aq-row">
      <div class="pt-aq-info">
        <span class="pt-aq-title">{{ $t('portal.admin.settings.autoQuota.title') }}</span>
        <span class="pt-aq-desc">{{ $t('portal.admin.settings.autoQuota.desc') }}</span>
      </div>
      <MkToggle
        :model-value="enabled"
        :disabled="saving"
        :aria-label="$t('portal.admin.settings.autoQuota.title')"
        @update:model-value="onToggle"
      />
    </div>

    <AutoQuotaHelp />

    <div v-if="enabled" class="pt-aq-config">
      <div v-for="f in FIELDS" :key="f.key" class="pt-aq-field">
        <label class="pt-aq-label" :for="ids[f.key]">
          {{ $t(`portal.admin.settings.autoQuota.${f.key}.label`) }}
        </label>
        <span class="pt-aq-hint">{{ $t(`portal.admin.settings.autoQuota.${f.key}.hint`) }}</span>
        <input
          :id="ids[f.key]"
          v-model.number="form[f.key]"
          type="number"
          class="pt-aq-input"
          :min="f.min"
          :max="f.max"
        />
      </div>

      <p v-if="boundsError" class="pt-aq-error">
        {{ $t('portal.admin.settings.autoQuota.boundsError') }}
      </p>

      <div class="pt-aq-actions">
        <button type="button" class="pt-aq-save" :disabled="saving || formInvalid" @click="onSave">
          <Save :size="14" />
          <span>{{ $t('common.save') }}</span>
        </button>
        <span v-if="savedMessage" class="pt-aq-saved">{{ savedMessage }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save } from 'lucide-vue-next'
import MkToggle from '@/components/common/MkToggle.vue'
import AutoQuotaHelp from '@/components/portal/admin/AutoQuotaHelp.vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const SAVED_MESSAGE_TIMEOUT_MS = 2000
const SETTINGS_URL = '/api/portal/admin/settings'

// key = quota.auto.<key> suffix (also the i18n sub-key); bounds mirror the
// backend PORTAL_SETTING_INTS registry.
const FIELDS = [
  { key: 'min', min: 1, max: 100 },
  { key: 'max', min: 1, max: 100 },
  { key: 'window_days', min: 1, max: 90 },
  { key: 'grace_days', min: 0, max: 90 },
  { key: 'up_step', min: 1, max: 50 },
  { key: 'down_step', min: 1, max: 50 },
]

const { t } = useI18n()
const { apiGet, apiPatch } = useApi()
const { showToast } = useToast()

const ids = Object.fromEntries(FIELDS.map(f => [f.key, useId()]))

const enabled = ref(true)
const form = reactive(Object.fromEntries(FIELDS.map(f => [f.key, f.min])))
const saving = ref(false)
const savedMessage = ref('')
let savedTimer = null

// Disable Save when any field is blank or out of range, so an emptied input
// cannot trigger a silent backend rejection without feedback.
// The default floor must not exceed the default ceiling (mirrors the per-user
// tab; the instance settings are otherwise saved without a cross-field check).
const boundsError = computed(() => Number(form.min) > Number(form.max))
const formInvalid = computed(
  () =>
    boundsError.value ||
    FIELDS.some(f => {
      const v = form[f.key]
      return !Number.isInteger(v) || v < f.min || v > f.max
    }),
)

function apply(res) {
  enabled.value = res['quota.auto.enabled']
  for (const f of FIELDS) form[f.key] = res[`quota.auto.${f.key}`]
}

function flashSaved() {
  savedMessage.value = t('common.saved')
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => {
    savedMessage.value = ''
  }, SAVED_MESSAGE_TIMEOUT_MS)
}

async function onToggle(next) {
  const prev = enabled.value
  enabled.value = next
  saving.value = true
  try {
    const res = await apiPatch(SETTINGS_URL, { 'quota.auto.enabled': next })
    if (res) {
      apply(res)
      flashSaved()
    }
  } catch (e) {
    enabled.value = prev
    console.error('[AdminAutoQuotaSetting.onToggle]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}

async function onSave() {
  if (formInvalid.value) return
  saving.value = true
  try {
    const payload = Object.fromEntries(FIELDS.map(f => [`quota.auto.${f.key}`, form[f.key]]))
    const res = await apiPatch(SETTINGS_URL, payload)
    if (res) {
      apply(res)
      flashSaved()
    }
  } catch (e) {
    console.error('[AdminAutoQuotaSetting.onSave]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await apiGet(SETTINGS_URL)
    if (res) apply(res)
  } catch (e) {
    console.error('[AdminAutoQuotaSetting.onMounted]', e)
    showToast(t('common.networkError'), TOAST_TYPE.ERR)
  }
})
</script>

<style scoped>
.pt-aq-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.pt-aq-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.pt-aq-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}
.pt-aq-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.pt-aq-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.35;
}
.pt-aq-config {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.pt-aq-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.pt-aq-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.pt-aq-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.35;
}
.pt-aq-input {
  width: 100%;
  margin-top: 0.25rem;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--text-sm);
  font-family: inherit;
}
.pt-aq-input:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-aq-error {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-error);
}
.pt-aq-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.pt-aq-save {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent);
  color: var(--color-on-accent);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  cursor: pointer;
}
.pt-aq-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.pt-aq-saved {
  font-size: var(--text-xs);
  color: var(--accent);
}
</style>
