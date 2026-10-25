<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.passwordTitle') }}</h3>
    </header>
    <p class="sec-desc">{{ t('settings.passwordDesc') }}</p>
    <form class="sec-pwd-form" @submit.prevent="submitPassword">
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.current') }}</span>
        <input
          v-model="current"
          type="password"
          autocomplete="current-password"
          :disabled="savingPwd"
        />
      </label>
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.new') }}</span>
        <input v-model="next" type="password" autocomplete="new-password" :disabled="savingPwd" />
      </label>
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.confirm') }}</span>
        <input
          v-model="confirm"
          type="password"
          autocomplete="new-password"
          :disabled="savingPwd"
        />
      </label>
      <ul class="sec-pwd-rules">
        <li>{{ t('forcePassword.rule12Chars') }}</li>
        <li>{{ t('forcePassword.ruleUpper') }}</li>
        <li>{{ t('forcePassword.ruleDigit') }}</li>
        <li>{{ t('forcePassword.ruleSpecial') }}</li>
      </ul>
      <div class="sec-pwd-actions">
        <button type="submit" class="sec-btn-primary" :disabled="!canSubmitPwd || savingPwd">
          {{ savingPwd ? t('forcePassword.submitting') : t('forcePassword.submit') }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { resolveApiError } from '@/composables/useApi'
import { useAuth } from '@/composables/useAuth'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const { t } = useI18n()
const { changePassword } = useAuth()
const { showToast } = useToast()

const current = ref('')
const next = ref('')
const confirm = ref('')
const savingPwd = ref(false)
const canSubmitPwd = computed(
  () => current.value && next.value && confirm.value && next.value.length >= 12,
)

async function submitPassword() {
  if (!canSubmitPwd.value) {
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
  savingPwd.value = true
  try {
    await changePassword(current.value, next.value)
    showToast(t('forcePassword.success'), TOAST_TYPE.OK)
    current.value = ''
    next.value = ''
    confirm.value = ''
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    savingPwd.value = false
  }
}
</script>

<style scoped>
.sec-desc {
  margin: 0 0 0.75rem;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.sec-pwd-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 420px;
}
.sec-pwd-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.sec-pwd-field input {
  padding: 9px 12px;
  border-radius: var(--radius-input);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
}
.sec-pwd-field input:focus {
  outline: none;
  border-color: var(--text-secondary);
}
.sec-pwd-rules {
  list-style: disc inside;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.1rem 0.8rem;
}
.sec-pwd-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
