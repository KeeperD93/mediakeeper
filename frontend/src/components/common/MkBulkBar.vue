<template>
  <Teleport to="body">
    <Transition name="bulk-slide">
      <div v-if="count > 0" class="bulk-bar" role="region" aria-live="polite">
        <span class="bulk-count"><slot name="count" /></span>
        <div class="bulk-actions"><slot /></div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
// Bulk-actions overlay that slides up from the bottom when rows are selected.
// `count` drives visibility; provide the count label via #count and the action
// buttons via the default slot. Teleported to body so it floats above the page.
defineProps({ count: { type: Number, required: true } })
</script>

<style scoped>
.bulk-bar {
  position: fixed;
  bottom: 24px;
  left: calc(50% + var(--sidebar-width) / 2);
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 20px;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-modal);
  backdrop-filter: var(--blur-md);
}
.bulk-count {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
}
.bulk-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bulk-slide-enter-active,
.bulk-slide-leave-active {
  transition:
    transform var(--duration-base) var(--ease-out),
    opacity var(--duration-base) var(--ease-out);
}
.bulk-slide-enter-from,
.bulk-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
@media (prefers-reduced-motion: reduce) {
  .bulk-slide-enter-active,
  .bulk-slide-leave-active {
    transition: opacity var(--duration-fast);
  }
  .bulk-slide-enter-from,
  .bulk-slide-leave-to {
    transform: translateX(-50%);
  }
}
@media (max-width: 767px) {
  .bulk-bar {
    bottom: 12px;
    left: 50%;
    padding: 10px 12px;
    gap: 10px;
    max-width: calc(100vw - 24px);
    flex-wrap: wrap;
    justify-content: center;
  }
  .bulk-actions {
    gap: 6px;
  }
}
</style>
