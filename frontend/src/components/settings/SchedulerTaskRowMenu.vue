<template>
  <div ref="menuEl" class="strm-menu" role="dialog" :aria-labelledby="descTitleId">
    <div class="strm-section">
      <div :id="descTitleId" class="strm-section-title">{{ $t('scheduler.description') }}</div>
      <div class="strm-description">
        {{ $t(task.description, task.description) }}
      </div>
    </div>
    <div v-if="task.last_error" class="strm-section">
      <div class="strm-section-title strm-error-title">{{ $t('scheduler.lastError') }}</div>
      <div class="strm-error-body">{{ task.last_error }}</div>
    </div>
    <div class="strm-actions">
      <button
        ref="resetBtnEl"
        type="button"
        class="strm-action-btn"
        :title="$t('scheduler.resetDefault', { v: formatSeconds(task.default_sec) })"
        @click="$emit('reset')"
      >
        <RotateCcw :size="13" />
        {{ $t('scheduler.reset') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, useId } from 'vue'
import { RotateCcw } from 'lucide-vue-next'

defineProps({
  task: { type: Object, required: true },
  formatSeconds: { type: Function, required: true },
})
const emit = defineEmits(['close', 'reset'])
const menuEl = ref(null)
const resetBtnEl = ref(null)
const descTitleId = useId()

function onDocumentClick(event) {
  if (menuEl.value && !menuEl.value.contains(event.target)) {
    emit('close')
  }
}
function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  // Defer the click listener by one frame so the same click that opens
  // the menu does not immediately close it.
  setTimeout(() => document.addEventListener('click', onDocumentClick), 0)
  document.addEventListener('keydown', onKeydown)
  // Move focus into the popover for keyboard users.
  nextTick(() => resetBtnEl.value?.focus())
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.strm-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 4px;
  right: 4px;
  min-width: 0;
  max-width: none;
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
  padding: 12px 14px;
  box-shadow: var(--shadow-md);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: strm-pop-in var(--duration-fast) var(--ease-out);
}
@keyframes strm-pop-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.strm-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.strm-section-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.strm-section-title.strm-error-title {
  color: var(--color-error);
}
.strm-description {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: var(--lh-normal);
}
.strm-error-body {
  font-size: var(--text-xs);
  color: var(--color-error);
  background: rgb(var(--color-error-rgb), 0.08);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono, monospace);
  overflow-wrap: anywhere;
}
.strm-actions {
  display: flex;
  gap: 6px;
  padding-top: 6px;
  border-top: 0.5px solid var(--border);
}
.strm-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 0.5px solid var(--border);
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  font-family: inherit;
  cursor: pointer;
  transition:
    background var(--duration-fast),
    border-color var(--duration-fast),
    color var(--duration-fast);
}
.strm-action-btn:focus-visible {
  outline: 2px solid var(--accent-500);
  outline-offset: 1px;
}
@media (hover: hover) {
  .strm-action-btn:hover {
    border-color: var(--border-hover);
    color: var(--text-primary);
  }
}
@media (min-width: 768px) {
  .strm-menu {
    left: auto;
    right: 8px;
    min-width: 260px;
    max-width: 340px;
  }
  .strm-action-btn {
    min-height: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .strm-menu {
    animation: none;
  }
  .strm-action-btn {
    transition: none;
  }
}
</style>
