<template>
  <Teleport to="body">
    <div
      v-if="state.open"
      class="mk-modal-sheet mk-confirm-overlay"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="state.title ? 'mk-confirm-title' : null"
      @click.self="cancel"
    >
      <div class="mk-modal-sheet-panel mk-confirm-panel">
        <h2 v-if="state.title" id="mk-confirm-title" class="mk-confirm-title">
          {{ state.title }}
        </h2>
        <p v-if="state.message" class="mk-confirm-message">
          {{ state.message }}
        </p>

        <div class="mk-confirm-actions">
          <button
            ref="cancelBtn"
            type="button"
            class="mk-confirm-btn mk-confirm-btn-cancel"
            @click="cancel"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="mk-confirm-btn mk-confirm-btn-confirm"
            :class="'mk-confirm-btn-' + state.variant"
            @click="accept"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { _useConfirmState } from '@/composables/useConfirm'

const { t } = useI18n()
const { state, accept, cancel } = _useConfirmState()

const cancelBtn = ref(null)

const confirmLabel = computed(() => state.value.confirmLabel || t('common.confirm'))
const cancelLabel = computed(() => state.value.cancelLabel || t('common.cancel'))

function onKey(e) {
  if (!state.value.open) return
  if (e.key === 'Escape') { e.preventDefault(); cancel() }
  else if (e.key === 'Enter') { e.preventDefault(); accept() }
}

watch(() => state.value.open, async (v) => {
  if (v) {
    window.addEventListener('keydown', onKey)
    await nextTick()
    cancelBtn.value?.focus()
  } else {
    window.removeEventListener('keydown', onKey)
  }
})
</script>

<style scoped>
.mk-confirm-overlay { z-index: 10000; }

.mk-confirm-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  padding: 24px 20px calc(20px + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mk-confirm-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.mk-confirm-message {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0;
  line-height: 1.5;
}

.mk-confirm-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.mk-confirm-btn {
  padding: 9px 16px;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border-radius: var(--radius-btn);
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--duration-base), color var(--duration-base), border-color var(--duration-base);
  min-width: 96px;
}

.mk-confirm-btn-cancel {
  background: transparent;
  color: var(--text-muted);
  border-color: var(--border-default);
}
@media (hover: hover) {
  .mk-confirm-btn-cancel:hover { color: var(--text-primary); border-color: var(--border-strong); }
}

.mk-confirm-btn-info {
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  border-color: rgba(var(--accent-rgb), 0.25);
}
@media (hover: hover) {
  .mk-confirm-btn-info:hover { background: rgba(var(--accent-rgb), 0.25); }
}

.mk-confirm-btn-warn {
  background: rgba(var(--color-warning-rgb), 0.15);
  color: var(--color-warning);
  border-color: rgba(var(--color-warning-rgb), 0.3);
}
@media (hover: hover) {
  .mk-confirm-btn-warn:hover { background: rgba(var(--color-warning-rgb), 0.25); }
}

.mk-confirm-btn-danger {
  background: rgba(var(--color-error-rgb), 0.15);
  color: var(--color-error);
  border-color: rgba(var(--color-error-rgb), 0.3);
}
@media (hover: hover) {
  .mk-confirm-btn-danger:hover { background: rgba(var(--color-error-rgb), 0.25); }
}

@media (min-width: 768px) {
  .mk-confirm-panel { padding: 24px; }
}
</style>
