<template>
  <Teleport to="body">
    <transition name="pt-dcm-fade">
      <div
        v-if="open"
        class="pt-dcm-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="onCancel"
      >
        <div class="pt-dcm-panel" tabindex="-1">
          <header class="pt-dcm-head">
            <AlertTriangle :size="22" class="pt-dcm-icon" />
            <h2 class="pt-dcm-title">
              {{ $t('portal.privacy.deleteModal.title') }}
            </h2>
          </header>

          <p class="pt-dcm-warning">
            {{ $t('portal.privacy.deleteModal.warning') }}
          </p>

          <p v-if="showEmbyNotice" class="pt-dcm-emby">
            {{ $t('portal.privacy.embyNotice') }}
          </p>

          <label class="pt-dcm-label" for="pt-dcm-input">
            <i18n-t keypath="portal.privacy.deleteModal.confirmLabel" tag="span">
              <template #word>
                <strong class="pt-dcm-word">{{ magicWord }}</strong>
              </template>
            </i18n-t>
          </label>

          <input
            id="pt-dcm-input"
            ref="inputRef"
            v-model="typed"
            class="pt-dcm-input"
            type="text"
            autocomplete="off"
            spellcheck="false"
          />

          <div class="pt-dcm-actions">
            <button
              type="button"
              class="pt-dcm-btn"
              :disabled="submitting"
              @click="onCancel"
            >
              {{ $t('portal.privacy.deleteModal.abort') }}
            </button>
            <button
              type="button"
              class="pt-dcm-btn pt-dcm-btn--danger"
              :disabled="!canConfirm || submitting"
              @click="onConfirm"
            >
              {{ submitting
                ? $t('portal.privacy.deleteModal.submitting')
                : $t('portal.privacy.deleteModal.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  submitting: { type: Boolean, default: false },
  // Only Emby-linked accounts see the "linked to Emby" reminder
  // (cf. PrivacyTab.vue isEmbyAccount). Local accounts hide it.
  showEmbyNotice: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])

const { t } = useI18n()

const typed = ref('')
const inputRef = ref(null)

// The magic word is part of the immutable contract: once typed, the
// confirmation button activates. We translate it so French users type
// "SUPPRIMER" and English users "DELETE" — but the comparison is
// case-sensitive on purpose so that pasted text or accidental caps
// lock cannot trigger the destructive action.
const magicWord = computed(() => t('portal.privacy.deleteModal.magicWord'))

const canConfirm = computed(() => typed.value.trim() === magicWord.value)

watch(() => props.open, async (open) => {
  if (!open) return
  typed.value = ''
  await nextTick()
  inputRef.value?.focus()
})

function onConfirm() {
  if (!canConfirm.value || props.submitting) return
  emit('confirm')
}

function onCancel() {
  if (props.submitting) return
  emit('cancel')
}
</script>

<style scoped>
.pt-dcm-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.pt-dcm-panel {
  width: 100%;
  max-width: 480px;
  background: var(--portal-surface-elevated, #1f1f24);
  color: var(--portal-text-primary, #fff);
  border: 1px solid var(--portal-border-default, rgba(255, 255, 255, 0.12));
  border-radius: 12px;
  padding: 1.4rem 1.5rem 1.25rem;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.55);
}
.pt-dcm-head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.5rem;
}
.pt-dcm-icon { color: #f59e0b; flex: 0 0 auto; }
.pt-dcm-title {
  margin: 0;
  font-size: var(--portal-text-lg);
  font-weight: var(--portal-font-extrabold);
}
.pt-dcm-warning {
  margin: 0 0 0.5rem;
  font-size: var(--portal-text-sm);
  color: var(--portal-text-secondary, rgba(255, 255, 255, 0.78));
  line-height: 1.5;
}
.pt-dcm-emby {
  margin: 0 0 0.85rem;
  padding: 0.55rem 0.75rem;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 8px;
  font-size: var(--portal-text-xs);
  color: #fcd34d;
}
.pt-dcm-label {
  display: block;
  font-size: var(--portal-text-xs);
  margin-bottom: 0.35rem;
  color: var(--portal-text-secondary);
}
.pt-dcm-word {
  font-family: var(--portal-font-mono, monospace);
  letter-spacing: 0.05em;
  color: #f87171;
}
.pt-dcm-input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  background: rgba(0, 0, 0, 0.35);
  color: var(--portal-text-primary);
  border: 1px solid var(--portal-border-default);
  border-radius: 8px;
  font-size: var(--portal-text-sm);
  font-family: var(--portal-font-mono, monospace);
}
.pt-dcm-input:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25);
}
.pt-dcm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.pt-dcm-btn {
  padding: 0.55rem 1rem;
  border-radius: 8px;
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  border: 1px solid var(--portal-border-default);
  background: transparent;
  color: var(--portal-text-primary);
  cursor: pointer;
  transition: background 0.18s ease;
}
.pt-dcm-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
}
.pt-dcm-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.pt-dcm-btn--danger {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #fff;
}
.pt-dcm-btn--danger:hover:not(:disabled) { background: #dc2626; }
.pt-dcm-btn--danger:disabled { background: rgba(185, 28, 28, 0.45); }

.pt-dcm-fade-enter-active, .pt-dcm-fade-leave-active {
  transition: opacity 0.2s ease;
}
.pt-dcm-fade-enter-from, .pt-dcm-fade-leave-to { opacity: 0; }
</style>
