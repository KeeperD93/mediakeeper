<template>
  <div v-if="show" class="pmlm-wrap">
    <button type="button" class="pmlm" :disabled="loading" @click="emit('load')">
      {{ loading ? $t('common.loading') : $t('common.loadMore') }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['load'])
</script>

<style scoped>
.pmlm-wrap {
  display: flex;
  justify-content: center;
  padding: 0.75rem 0 0.25rem;
}
.pmlm {
  min-height: 44px;
  padding: 8px 18px;
  border: 1px solid var(--portal-border-default);
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
  color: var(--portal-text-body-muted);
  font-family: inherit;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  cursor: pointer;
  transition:
    background-color var(--portal-dur-fast),
    border-color var(--portal-dur-fast),
    color var(--portal-dur-fast);
}
.pmlm:disabled {
  opacity: 0.6;
  cursor: default;
}
@media (hover: hover) {
  .pmlm:not(:disabled):hover {
    border-color: var(--portal-border-intense);
    color: var(--portal-text-primary);
  }
}
.pmlm:focus-visible {
  outline: 2px solid rgb(var(--portal-accent-rgb), 0.4);
  outline-offset: 1px;
}
</style>
