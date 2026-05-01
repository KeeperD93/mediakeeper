<template>
  <div>
    <h2 class="params-title">{{ $t('settings.tabTest') }}</h2>
    <p class="params-desc">{{ $t('settings.testDesc') }}</p>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.testToastTitle') }}</h3>
      <p class="params-section-desc">{{ $t('settings.testToastDesc') }}</p>
      <div class="test-toast-grid">
        <button class="test-toast-btn test-toast-ok" @click="testToast('ok')">
          <Check :size="14" :stroke-width="2.5" />
          {{ $t('settings.testToastOk') }}
        </button>
        <button class="test-toast-btn test-toast-err" @click="testToast('err')">
          <X :size="14" :stroke-width="2.5" />
          {{ $t('settings.testToastErr') }}
        </button>
        <button class="test-toast-btn test-toast-warn" @click="testToast('warn')">
          <TriangleAlert :size="14" :stroke-width="2.5" />
          {{ $t('settings.testToastWarn') }}
        </button>
        <button class="test-toast-btn test-toast-media" @click="testToast('media')">
          <CirclePlay :size="14" />
          {{ $t('settings.testToastMedia') }}
        </button>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.testWizardTitle') }}</h3>
      <p class="params-section-desc">{{ $t('settings.testWizardDesc') }}</p>
      <div class="params-test-actions">
        <button class="params-danger-btn params-danger-btn-preview" @click="showOnboardingPreview = true">
          {{ $t('settings.previewOnboarding') }}
        </button>
        <button class="params-danger-btn" @click="resetOnboarding">
          {{ $t('settings.resetOnboarding') }}
        </button>
      </div>
    </section>

    <OnboardingWizard v-if="showOnboardingPreview" :force-show="true" @done="showOnboardingPreview = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import OnboardingWizard from '@/components/OnboardingWizard.vue'
import { Check, CirclePlay, TriangleAlert, X } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { apiFetch } = useApi()
const { showToast } = useToast()

const showOnboardingPreview = ref(false)

function testToast(type) {
  const messages = {
    ok: t('settings.testToastMsgOk'),
    err: t('settings.testToastMsgErr'),
    warn: t('settings.testToastMsgWarn'),
    media: t('settings.testToastMsgMedia'),
  }
  const meta = type === 'media' ? { subtitle: 'Film · 2024' } : null
  showToast(messages[type] || 'Test', type, 5000, meta)
}

async function resetOnboarding() {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.reset'),
    message: t('settings.resetOnboardingConfirm'),
    variant: 'warn',
  })
  if (!ok) return
  await apiFetch('/api/onboarding/reset', { method: 'POST' })
  showToast(t('settings.resetOnboardingDone'), TOAST_TYPE.OK)
  window.location.reload()
}
</script>

<style scoped>
.test-toast-grid { display: flex; gap: 8px; flex-wrap: wrap; }
.test-toast-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 9px 18px; border-radius: var(--radius-btn);
  font-size: var(--text-sm); font-weight: var(--font-medium); cursor: pointer;
  font-family: inherit; border: .5px solid var(--border);
  background: var(--bg-secondary); color: var(--text-secondary);
  transition: all var(--duration-fast);
}
.test-toast-ok:hover   { border-color: var(--color-success); color: var(--color-success); background: rgba(var(--color-success-rgb),.08); }
.test-toast-err:hover  { border-color: var(--color-error); color: var(--color-error); background: rgba(var(--color-error-rgb),.08); }
.test-toast-warn:hover { border-color: var(--color-warning); color: var(--color-warning); background: rgba(var(--color-warning-rgb),.08); }
.test-toast-media:hover { border-color: var(--accent-400); color: var(--accent-400); background: rgba(var(--accent-rgb),.08); }
.params-test-actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
