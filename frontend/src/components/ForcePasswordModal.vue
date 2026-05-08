<template>
  <div class="mk-modal-sheet fpm-overlay">
    <div class="mk-modal-sheet-panel fpm-panel">
      <!-- Header -->
      <div class="text-center mb-7">
        <div
          class="w-14 h-14 bg-indigo-700/20 border border-indigo-700/40 rounded-full flex items-center justify-center mx-auto mb-4"
        >
          <Lock class="w-6 h-6 text-indigo-400" :stroke-width="2" />
        </div>
        <h2 class="text-lg font-bold mb-2 fpm-title">{{ $t('forcePassword.title') }}</h2>
        <p class="text-[0.82rem] fpm-muted">{{ $t('forcePassword.description') }}</p>
      </div>

      <!-- Error -->
      <div
        v-if="errorMsg"
        class="bg-red-900/25 border border-red-800/40 rounded-lg px-3.5 py-2.5 text-[0.8rem] text-red-300 mb-4"
      >
        {{ errorMsg }}
      </div>

      <!-- Formulaire -->
      <div class="flex flex-col gap-3.5">
        <div>
          <label class="block text-[0.78rem] mb-1.5 fpm-label">
            {{ $t('forcePassword.current') }}
          </label>
          <input
            v-model="currentPwd"
            type="password"
            placeholder="••••••••"
            class="fpm-input w-full rounded-lg px-3 py-2 text-[0.85rem] outline-hidden transition-colors box-border"
          />
        </div>

        <div>
          <label class="block text-[0.78rem] mb-1.5 fpm-label">{{ $t('forcePassword.new') }}</label>
          <input
            v-model="newPwd"
            type="password"
            :placeholder="$t('forcePassword.rule12Chars')"
            class="fpm-input w-full rounded-lg px-3 py-2 text-[0.85rem] outline-hidden transition-colors box-border"
          />
          <div class="mt-2 px-3 py-2.5 bg-indigo-700/10 border border-indigo-700/30 rounded-md">
            <p class="text-indigo-400 text-xs font-semibold mb-1.5">
              {{ $t('forcePassword.rules') }}
            </p>
            <ul class="text-xs list-none p-0 m-0 flex flex-col gap-1 fpm-label">
              <li>&#10003; {{ $t('forcePassword.rule12Chars') }}</li>
              <li>&#10003; {{ $t('forcePassword.rule12Unique') }}</li>
              <li>&#10003; {{ $t('forcePassword.ruleUpper') }}</li>
              <li>&#10003; {{ $t('forcePassword.ruleDigit') }}</li>
              <li>&#10003; {{ $t('forcePassword.ruleSpecial') }}</li>
            </ul>
          </div>
        </div>

        <div>
          <label class="block text-[0.78rem] mb-1.5 fpm-label">
            {{ $t('forcePassword.confirm') }}
          </label>
          <input
            v-model="confirmPwd"
            type="password"
            placeholder="••••••••"
            class="fpm-input w-full rounded-lg px-3 py-2 text-[0.85rem] outline-hidden transition-colors box-border"
          />
        </div>

        <button
          :disabled="submitting"
          class="bg-indigo-600 text-white border-none rounded-lg p-3 text-[0.875rem] font-semibold cursor-pointer w-full mt-1 hover:bg-indigo-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          @click="submit"
        >
          {{ submitting ? $t('forcePassword.submitting') : $t('forcePassword.submit') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { Lock } from 'lucide-vue-next'

const { t } = useI18n()
const { changePassword } = useAuth()
const { showToast } = useToast()

const currentPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const errorMsg = ref('')
const submitting = ref(false)

async function submit() {
  errorMsg.value = ''

  if (!currentPwd.value || !newPwd.value || !confirmPwd.value) {
    errorMsg.value = t('forcePassword.allRequired')
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    errorMsg.value = t('forcePassword.mismatch')
    return
  }
  if (newPwd.value.length < 12) {
    errorMsg.value = t('forcePassword.tooShort')
    return
  }

  submitting.value = true
  try {
    await changePassword(currentPwd.value, newPwd.value)
    showToast(t('forcePassword.success'), TOAST_TYPE.OK)
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.fpm-overlay {
  z-index: 1000;
}
.fpm-panel {
  padding: 2rem 1.25rem;
  max-width: 440px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
}
.fpm-title {
  color: var(--text-primary);
}
.fpm-muted {
  color: var(--text-muted);
}
.fpm-label {
  color: var(--text-secondary);
}
.fpm-input {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-primary);
}
.fpm-input:focus {
  border-color: var(--accent-600, #4f46e5);
}
@media (min-width: 768px) {
  .fpm-panel {
    padding: 2.5rem;
  }
}
</style>
