<template>
  <Teleport to="body">
    <div
      class="mk-modal-sheet"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.self="close"
    >
      <form ref="panelRef" class="sec-modal mk-modal-sheet-panel" @submit.prevent="submitBlock">
        <h2 :id="titleId">{{ t('settings.security.addBlock') }}</h2>
        <label>
          {{ t('settings.security.ip') }}
          <input
            ref="ipRef"
            v-model.trim="form.ip"
            :maxlength="BLOCK_FIELD_MAX.IP"
            placeholder="192.0.2.0"
          />
        </label>
        <label>
          {{ t('settings.security.username') }}
          <input v-model.trim="form.username" :maxlength="BLOCK_FIELD_MAX.USERNAME" />
        </label>
        <label>
          {{ t('settings.security.scope') }}
          <select v-model="form.scope" class="sec-select mk-select-chevron">
            <option v-for="scope in MANUAL_BLOCK_SCOPES" :key="scope" :value="scope">
              {{ scopeLabel(scope) }}
            </option>
          </select>
        </label>
        <label>
          {{ t('settings.security.reason') }}
          <input v-model.trim="form.reason" :maxlength="BLOCK_FIELD_MAX.REASON" />
        </label>
        <p class="sec-modal-hint">{{ t('settings.security.permanentHint') }}</p>
        <div class="sec-modal-actions">
          <button type="button" class="sec-btn" :disabled="busy" @click="close">
            {{ t('common.cancel') }}
          </button>
          <button type="submit" class="sec-btn-primary" :disabled="busy">
            {{ t('common.save') }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useToast } from '@/composables/useToast'
import { BLOCK_FIELD_MAX, MANUAL_BLOCK_SCOPES, SECURITY_SCOPE } from '@/constants/security'
import { TOAST_TYPE } from '@/constants/toast'

const props = defineProps({
  busy: { type: Boolean, required: true },
  scopeLabel: { type: Function, required: true },
})
const emit = defineEmits(['close', 'submit'])

const { t } = useI18n()
const { showToast } = useToast()

const titleId = useId()
const panelRef = ref(null)
const ipRef = ref(null)
// Manual blocks are permanent: an admin lifts them under "Active blocks".
const form = ref({ ip: '', username: '', scope: SECURITY_SCOPE.ALL, reason: '' })

function close() {
  if (props.busy) return
  emit('close')
}

function submitBlock() {
  if (!form.value.ip && !form.value.username) {
    showToast(t('settings.security.needIpOrUser'), TOAST_TYPE.ERR)
    return
  }
  emit('submit', { ...form.value, permanent: true })
}

useFocusTrap({
  active: ref(true),
  containerRef: panelRef,
  initialFocusRef: ipRef,
  onEscape: close,
})
</script>

<style scoped>
.sec-modal {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-6);
  padding-inline: var(--space-6);
  padding-bottom: calc(var(--space-6) + env(safe-area-inset-bottom, 0px));
}
@media (min-width: 768px) {
  .sec-modal {
    max-width: 420px;
  }
}
.sec-modal h2 {
  margin: 0 0 var(--space-2);
}
.sec-modal label {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
}
.sec-modal input {
  padding: var(--space-2);
  border-radius: var(--radius-input);
  border: var(--border-width) solid var(--border);
  background: var(--bg-secondary);
  color: inherit;
}
.sec-select {
  min-height: var(--touch-target);
  padding-left: var(--space-3);
  padding-block: 0;
  border-radius: var(--radius-input);
  border: var(--border-width) solid var(--border);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}
@media (min-width: 768px) {
  .sec-select {
    min-height: 0;
    padding-block: var(--space-2);
  }
}
.sec-modal input:focus-visible,
.sec-select:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* iOS zooms into a field under 16px it focuses: 16px there only. */
@supports (-webkit-touch-callout: none) {
  .sec-modal input,
  .sec-select {
    font-size: var(--text-md);
  }
}
.sec-modal-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.sec-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
</style>
