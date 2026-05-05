<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="visible" class="sub-modal-overlay mk-modal-sheet" @click.self="$emit('close')">
        <div class="sub-modal glass-card mk-modal-sheet-panel">
          <h3 class="sub-modal-title">{{ $t('subtitles.downloadAuto') }}</h3>
          <div class="sub-modal-field">
            <input
              v-model="dest"
              class="sub-modal-input"
              placeholder="/media/Movie/Movie.fr.srt"
              @keydown.enter="confirm"
            />
          </div>
          <div class="sub-modal-actions">
            <button class="sub-modal-cancel" @click="$emit('close')">
              {{ $t('common.cancel') }}
            </button>
            <button class="sub-modal-save" :disabled="!dest.trim()" @click="confirm">
              {{ $t('subtitles.downloadAuto') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  defaultPath: { type: String, default: '' },
})
const emit = defineEmits(['close', 'confirm'])

const dest = ref('')

watch(
  () => props.defaultPath,
  v => {
    dest.value = v
  },
  { immediate: true },
)

function confirm() {
  if (dest.value.trim()) {
    emit('confirm', dest.value.trim())
  }
}
</script>

<style scoped>
/* Layout delegated to .mk-modal-sheet + .mk-modal-sheet-panel.
   Only the component-specific sizing stays, applied desktop-only. */
.sub-modal-overlay {
  z-index: 1000;
}
@media (min-width: 768px) {
  .sub-modal {
    width: 420px;
    padding: 22px;
  }
}
.sub-modal-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 14px;
}
.sub-modal-field {
  margin-bottom: 14px;
}
.sub-modal-input {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}
.sub-modal-input:focus {
  border-color: rgb(var(--accent-rgb), 0.4);
}
.sub-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.sub-modal-cancel,
.sub-modal-save {
  padding: 7px 16px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.sub-modal-cancel {
  background: var(--surface-2);
  color: var(--text-secondary);
}
.sub-modal-save {
  background: var(--accent-500);
  color: #fff;
}
.sub-modal-save:hover:not(:disabled) {
  opacity: 0.9;
}
.sub-modal-save:disabled {
  opacity: 0.4;
  cursor: default;
}
.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}

.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity var(--duration-base);
}
.sub-fade-enter-from,
.sub-fade-leave-to {
  opacity: 0;
}
</style>
