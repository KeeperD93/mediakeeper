<template>
  <transition name="set-bar">
    <div
      v-if="dirty"
      class="set-save-bar"
      role="region"
      :aria-label="$t('portal.admin.settings.saveBar.label')"
    >
      <span class="set-save-bar-text">
        {{
          invalid
            ? $t('portal.admin.settings.saveBar.invalid')
            : $t('portal.admin.settings.saveBar.unsaved')
        }}
      </span>
      <div class="set-save-bar-actions">
        <button
          type="button"
          class="set-bar-btn set-bar-btn--ghost"
          :disabled="saving"
          @click="$emit('reset')"
        >
          {{ $t('portal.admin.settings.saveBar.discard') }}
        </button>
        <button
          type="button"
          class="set-bar-btn set-bar-btn--primary"
          :disabled="saving || invalid"
          @click="$emit('save')"
        >
          {{ $t('common.save') }}
        </button>
      </div>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  dirty: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
})
defineEmits(['save', 'reset'])
</script>

<style scoped>
.set-save-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.85rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.set-save-bar-text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.set-save-bar-actions {
  display: flex;
  gap: 0.6rem;
}
/* Button styling (.set-bar-btn*) is shared and lives in admin-settings.css so
   per-card panels (e.g. maintenance) reuse the same buttons. */
.set-bar-enter-active,
.set-bar-leave-active {
  transition:
    transform var(--duration-base),
    opacity var(--duration-base);
}
.set-bar-enter-from,
.set-bar-leave-to {
  transform: translateY(0.5rem);
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .set-bar-enter-active,
  .set-bar-leave-active {
    transition: none;
  }
}
</style>
