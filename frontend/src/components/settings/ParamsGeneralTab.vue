<template>
  <div>
    <h2 class="params-title">{{ $t('settings.tabGeneral') }}</h2>
    <p class="params-desc">{{ $t('settings.generalDesc') }}</p>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.languageLabel') }}</h3>
      <p class="params-section-desc">{{ $t('settings.languageDesc') }}</p>
      <div class="params-lang-select-wrap">
        <select class="params-lang-select" :value="currentLocale" @change="onLocaleChange($event.target.value)">
          <option v-for="loc in AVAILABLE_LOCALES" :key="loc.code" :value="loc.code">
            {{ loc.flag }} {{ loc.label }}
          </option>
        </select>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.passwordTitle') }}</h3>
      <p class="params-section-desc">{{ $t('settings.passwordDesc') }}</p>
      <form class="params-pwd-form" @submit.prevent="submit">
        <label class="params-pwd-field">
          <span>{{ $t('forcePassword.current') }}</span>
          <input v-model="current" type="password" autocomplete="current-password" :disabled="saving" />
        </label>
        <label class="params-pwd-field">
          <span>{{ $t('forcePassword.new') }}</span>
          <input v-model="next" type="password" autocomplete="new-password" :disabled="saving" />
        </label>
        <label class="params-pwd-field">
          <span>{{ $t('forcePassword.confirm') }}</span>
          <input v-model="confirm" type="password" autocomplete="new-password" :disabled="saving" />
        </label>
        <ul class="params-pwd-rules">
          <li>{{ $t('forcePassword.rule12Chars') }}</li>
          <li>{{ $t('forcePassword.ruleUpper') }}</li>
          <li>{{ $t('forcePassword.ruleDigit') }}</li>
          <li>{{ $t('forcePassword.ruleSpecial') }}</li>
        </ul>
        <div class="params-pwd-actions">
          <button type="submit" class="params-pwd-submit" :disabled="!canSubmit || saving">
            {{ saving ? $t('forcePassword.submitting') : $t('forcePassword.submit') }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale, getLocale, AVAILABLE_LOCALES } from '@/i18n'
import { useAuth } from '@/composables/useAuth'
import { resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const { t } = useI18n()
const { changePassword } = useAuth()
const { showToast } = useToast()

const currentLocale = ref(getLocale())
const current = ref('')
const next = ref('')
const confirm = ref('')
const saving = ref(false)

const canSubmit = computed(() =>
  current.value && next.value && confirm.value && next.value.length >= 12,
)

async function onLocaleChange(code) {
  const changed = await setLocale(code)
  if (changed) currentLocale.value = code
}

async function submit() {
  if (!canSubmit.value) {
    showToast(t('forcePassword.allRequired'), TOAST_TYPE.ERR)
    return
  }
  if (next.value !== confirm.value) {
    showToast(t('forcePassword.mismatch'), TOAST_TYPE.ERR)
    return
  }
  if (next.value.length < 12) {
    showToast(t('forcePassword.tooShort'), TOAST_TYPE.ERR)
    return
  }
  saving.value = true
  try {
    await changePassword(current.value, next.value)
    showToast(t('forcePassword.success'), TOAST_TYPE.OK)
    current.value = ''
    next.value = ''
    confirm.value = ''
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.params-lang-select-wrap { max-width: 260px; }
.params-lang-select {
  width: 100%; padding: 9px 14px; border-radius: var(--radius-btn);
  border: .5px solid var(--border); background: var(--bg-secondary);
  color: var(--text-primary); font-size: var(--text-sm); font-family: inherit;
  cursor: pointer; appearance: auto;
}
.params-lang-select:focus { outline: none; border-color: var(--accent-500); }

.params-pwd-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 420px;
}
.params-pwd-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: var(--text-sm);
  color: var(--text-secondary));
}
.params-pwd-field input {
  padding: 9px 12px;
  border-radius: var(--radius-input);
  border: .5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
}
.params-pwd-field input:focus {
  outline: none;
  border-color: var(--accent-500);
}
.params-pwd-rules {
  list-style: disc inside;
  font-size: var(--text-xs);
  color: var(--text-secondary));
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.1rem 0.8rem;
}
.params-pwd-actions {
  display: flex;
  justify-content: flex-end;
}
.params-pwd-submit {
  padding: 9px 18px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent-500);
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}
.params-pwd-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
