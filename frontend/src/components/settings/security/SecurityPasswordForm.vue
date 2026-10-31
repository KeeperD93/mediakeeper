<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.passwordTitle') }}</h3>
    </header>
    <p class="sec-desc">{{ t('settings.passwordDesc') }}</p>
    <!-- A new form after a change: password managers take the old one's removal
         as the end of the change and offer to update the saved password. -->
    <form :key="formKey" class="sec-pwd-form" @submit.prevent="submitPassword">
      <input
        type="text"
        name="username"
        autocomplete="username"
        :value="user?.username || ''"
        readonly
        hidden
      />
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.current') }}</span>
        <input
          v-model="currentPwd"
          type="password"
          autocomplete="current-password"
          :disabled="savingPwd"
        />
      </label>
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.new') }}</span>
        <input v-model="newPwd" type="password" autocomplete="new-password" :disabled="savingPwd" />
      </label>
      <label class="sec-pwd-field">
        <span>{{ t('forcePassword.confirm') }}</span>
        <input
          v-model="confirmPwd"
          type="password"
          autocomplete="new-password"
          :disabled="savingPwd"
        />
      </label>
      <ul class="sec-pwd-rules">
        <li>{{ t('forcePassword.rule12Chars') }}</li>
        <li>{{ t('forcePassword.rule12Unique') }}</li>
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
import { PASSWORD_MIN_LENGTH } from '@/constants/auth'
import { TOAST_TYPE } from '@/constants/toast'

// Emitted after every try: a password change, right or wrong, shows in "Recent attempts".
const emit = defineEmits(['attempted'])

const { t } = useI18n()
const { user, changePassword } = useAuth()
const { showToast } = useToast()

const currentPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const savingPwd = ref(false)
const formKey = ref(0)
// The button stays disabled until every field is filled and the new one is long enough.
const canSubmitPwd = computed(
  () =>
    currentPwd.value &&
    newPwd.value &&
    confirmPwd.value &&
    newPwd.value.length >= PASSWORD_MIN_LENGTH,
)

async function submitPassword() {
  if (newPwd.value !== confirmPwd.value) {
    showToast(t('forcePassword.mismatch'), TOAST_TYPE.ERR)
    return
  }
  savingPwd.value = true
  try {
    await changePassword(currentPwd.value, newPwd.value)
    showToast(t('forcePassword.success'), TOAST_TYPE.OK)
    currentPwd.value = ''
    newPwd.value = ''
    confirmPwd.value = ''
    formKey.value++
  } catch (e) {
    console.error('[SecurityPasswordForm.submitPassword]', e)
    showToast(resolveApiError(e.message, 'common.apiError.saveFailed'), TOAST_TYPE.ERR)
  } finally {
    savingPwd.value = false
    emit('attempted')
  }
}
</script>

<style scoped>
.sec-desc {
  margin: 0 0 var(--space-3);
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
  min-height: var(--touch-target);
  padding: 9px var(--space-3);
  border-radius: var(--radius-input);
  border: var(--border-width-thin) solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
}
@media (min-width: 768px) {
  .sec-pwd-field input {
    min-height: 0;
  }
}
.sec-pwd-field input:focus {
  outline: none;
  border-color: var(--text-secondary);
}
.sec-pwd-field input:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* iOS zooms into a field under 16px it focuses: 16px there only. */
@supports (-webkit-touch-callout: none) {
  .sec-pwd-field input {
    font-size: var(--text-md);
  }
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
