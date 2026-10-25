<template>
  <div class="sec-modal-backdrop mk-modal-sheet" @click.self="emit('close')">
    <div
      class="sec-modal mk-modal-sheet-panel"
      role="dialog"
      :aria-label="t('settings.security.addBlock')"
    >
      <h4>{{ t('settings.security.addBlock') }}</h4>
      <label>
        {{ t('settings.security.ip') }}
        <input v-model.trim="form.ip" placeholder="192.0.2.0" />
      </label>
      <label>
        {{ t('settings.security.username') }}
        <input v-model.trim="form.username" placeholder="attacker" />
      </label>
      <label>
        {{ t('settings.security.scope') }}
        <select v-model="form.scope">
          <option value="all">all</option>
          <option value="admin">admin</option>
          <option value="portal">portal</option>
        </select>
      </label>
      <label>
        <input v-model="form.permanent" type="checkbox" />
        {{ t('settings.security.permanent') }}
      </label>
      <label>
        {{ t('settings.security.reason') }}
        <input v-model.trim="form.reason" />
      </label>
      <div class="sec-modal-actions">
        <button class="sec-btn" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button class="sec-btn-primary" @click="submitBlock">{{ t('common.save') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const emit = defineEmits(['close', 'submit'])

const { t } = useI18n()
const { showToast } = useToast()

const form = ref({ ip: '', username: '', scope: 'all', permanent: true, reason: '' })

function submitBlock() {
  if (!form.value.ip && !form.value.username) {
    showToast(t('settings.security.needIpOrUser'), TOAST_TYPE.ERR)
    return
  }
  emit('submit', { ...form.value })
}
</script>

<style scoped>
.sec-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgb(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.sec-modal {
  background: var(--bg-panel);
  border-radius: var(--radius-card);
  padding: 1.5rem;
  max-width: 420px;
  width: 90%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.sec-modal h4 {
  margin: 0 0 0.5rem;
}
.sec-modal label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: var(--text-sm);
}
.sec-modal input,
.sec-modal select {
  padding: 0.5rem;
  border-radius: var(--radius-input);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: inherit;
}
.sec-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
