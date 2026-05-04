<template>
  <div class="pt-settings-card pt-privacy">
    <h3 class="pt-settings-section-title">
      {{ $t('portal.privacy.policy.title') }}
    </h3>
    <p v-if="dpoContact" class="pt-settings-section-sub pt-privacy-dpo">
      <i18n-t keypath="portal.privacy.dpo" tag="span">
        <template #contact>
          <strong>{{ dpoContact }}</strong>
        </template>
      </i18n-t>
    </p>

    <div v-if="loading" class="pt-privacy-loading">
      {{ $t('common.loading') }}
    </div>
    <!-- Server already runs the text through bleach on admin write;
         DOMPurify here is defence in depth (HelpCardList pattern). -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div
      v-else-if="purifiedHtml"
      class="pt-privacy-text pt-help-article-body"
      v-html="purifiedHtml"
    />
    <p v-else class="pt-privacy-empty">
      {{ $t('portal.privacy.policy.notConfigured') }}
    </p>

    <hr class="pt-settings-divider" />

    <h3 class="pt-settings-section-title">
      {{ $t('portal.privacy.data.title') }}
    </h3>
    <p class="pt-settings-section-sub">
      {{ $t('portal.privacy.data.subtitle') }}
    </p>

    <div class="pt-privacy-actions">
      <button
        type="button"
        class="pt-settings-btn"
        :disabled="exporting"
        @click="onExport"
      >
        <Download :size="14" />
        {{ exporting
          ? $t('portal.privacy.data.exporting')
          : $t('portal.privacy.data.exportBtn') }}
      </button>

      <button
        type="button"
        class="pt-settings-btn pt-privacy-delete"
        :disabled="modalOpen || submittingDeletion"
        @click="modalOpen = true"
      >
        <Trash2 :size="14" />
        {{ $t('portal.privacy.data.deleteBtn') }}
      </button>
    </div>

    <p v-if="isEmbyAccount" class="pt-privacy-emby-final">
      {{ $t('portal.privacy.embyNotice') }}
    </p>

    <DeleteConfirmModal
      :open="modalOpen"
      :submitting="submittingDeletion"
      :show-emby-notice="isEmbyAccount"
      @confirm="onConfirmDeletion"
      @cancel="modalOpen = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import { Download, Trash2 } from 'lucide-vue-next'

import {
  EXPORT_LIMIT, EXPORT_TOO_LARGE, useGdprUser,
} from '@/composables/portal/useGdprUser'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import DeleteConfirmModal from './DeleteConfirmModal.vue'

const { t, locale } = useI18n()
const { showToast } = useToast()
const { profile, refreshAuth } = usePortalAuth()
const { getPrivacyText, exportMyData, submitDeletion } = useGdprUser()

const loading = ref(false)
const textHtml = ref('')
const dpoContact = ref('')
const exporting = ref(false)
const modalOpen = ref(false)
const submittingDeletion = ref(false)

// The "linked to Emby" reminder only makes sense for Emby-sourced
// accounts. Locally-created accounts (admin or manual) get no such
// notice — the message would be misleading.
const isEmbyAccount = computed(() => profile.value?.source === 'emby')

// Server already sanitises through bleach on the admin write path —
// DOMPurify here is defence in depth, mirroring HelpCardList. If the
// backend ever regresses, the rendered HTML stays scrubbed.
const purifiedHtml = computed(() => {
  if (!textHtml.value) return ''
  return DOMPurify.sanitize(String(textHtml.value))
})

async function loadText() {
  loading.value = true
  try {
    const res = await getPrivacyText(locale.value)
    textHtml.value = res?.text_html || ''
    dpoContact.value = res?.dpo_contact || ''
  } catch {
    textHtml.value = ''
    dpoContact.value = ''
  } finally {
    loading.value = false
  }
}

watch(locale, loadText)
onMounted(loadText)

function formatRetryAfter(retryAfter) {
  if (!retryAfter) return ''
  const seconds = Number(retryAfter)
  if (Number.isFinite(seconds) && seconds > 0) {
    const at = new Date(Date.now() + seconds * 1000)
    return at.toLocaleTimeString(locale.value, {
      hour: '2-digit', minute: '2-digit',
    })
  }
  // HTTP-date form — pass through as-is.
  return String(retryAfter)
}

async function onExport() {
  if (exporting.value) return
  exporting.value = true
  try {
    await exportMyData()
    showToast(t('portal.privacy.data.exportStarted'), TOAST_TYPE.OK)
  } catch (err) {
    if (err?.code === EXPORT_LIMIT) {
      const when = formatRetryAfter(err.retryAfter)
      showToast(
        when
          ? t('portal.privacy.data.exportLimitedAt', { when })
          : t('portal.privacy.data.exportLimited'),
        TOAST_TYPE.ERR,
      )
    } else if (err?.code === EXPORT_TOO_LARGE) {
      showToast(t('portal.privacy.data.exportTooLarge'), TOAST_TYPE.ERR)
    } else {
      showToast(t('portal.privacy.data.exportFailed'), TOAST_TYPE.ERR)
    }
  } finally {
    exporting.value = false
  }
}

async function onConfirmDeletion() {
  if (submittingDeletion.value) return
  submittingDeletion.value = true
  try {
    const res = await submitDeletion()
    await refreshAuth()
    modalOpen.value = false
    if (res.alreadyPending) {
      // Backend already had a pending request — banner is now visible
      // with the existing schedule. No second toast needed since the
      // visual change is the answer.
      return
    }
    showToast(t('portal.privacy.deleteModal.scheduled'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.privacy.deleteModal.failed'), TOAST_TYPE.ERR)
  } finally {
    submittingDeletion.value = false
  }
}
</script>

<style scoped>
.pt-privacy-loading,
.pt-privacy-empty {
  padding: 0.75rem 0;
  font-size: var(--portal-text-sm);
  color: var(--portal-text-secondary);
}
.pt-privacy-empty {
  font-style: italic;
}
.pt-privacy-text {
  margin-top: 0.25rem;
  padding: 0.85rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--portal-border-faint);
  border-radius: 10px;
  font-size: var(--portal-text-sm);
  line-height: 1.55;
  max-height: 360px;
  overflow-y: auto;
}
.pt-privacy-text :deep(p) { margin: 0 0 0.6em; }
.pt-privacy-text :deep(p:last-child) { margin-bottom: 0; }
.pt-privacy-text :deep(h2),
.pt-privacy-text :deep(h3) {
  margin: 0.85em 0 0.4em;
  font-size: var(--portal-text-base);
}
.pt-privacy-text :deep(ul),
.pt-privacy-text :deep(ol) { padding-left: 1.2em; }

.pt-privacy-dpo {
  margin-bottom: 0.5rem;
}

.pt-settings-divider {
  border: none;
  border-top: 1px solid var(--portal-border-default);
  margin: 1.25rem 0 0.75rem;
}

.pt-privacy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.75rem;
}
.pt-privacy-delete {
  border-color: rgba(248, 113, 113, 0.45);
  color: #fecaca;
}
.pt-privacy-delete:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.12);
}

.pt-privacy-emby-final {
  margin-top: 1rem;
  padding: 0.6rem 0.85rem;
  border-left: 3px solid var(--portal-color-info, #60a5fa);
  background: rgba(96, 165, 250, 0.08);
  border-radius: 6px;
  font-size: var(--portal-text-xs);
  color: var(--portal-text-secondary);
  line-height: 1.45;
}
</style>
