<template>
  <div
    class="mk-spinner"
    :class="['mk-spinner-' + size, { 'mk-spinner-inline': inline }]"
    role="status"
    aria-live="polite"
  />
</template>

<script setup>
defineProps({
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg'].includes(v),
  },
  inline: { type: Boolean, default: false },
})
</script>

<style scoped>
.mk-spinner {
  display: block;
  margin: 0 auto;
  border-style: solid;
  border-color: var(--border-default);
  border-top-color: var(--accent-500);
  border-radius: 50%;
  animation: mk-spinner-spin 0.8s linear infinite;
}

.mk-spinner-inline {
  display: inline-block;
  margin: 0;
  vertical-align: middle;
}

.mk-spinner-sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.mk-spinner-md {
  width: 24px;
  height: 24px;
  border-width: 2.5px;
}

.mk-spinner-lg {
  width: 36px;
  height: 36px;
  border-width: 3px;
}

@keyframes mk-spinner-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .mk-spinner {
    animation-duration: 2s;
  }
}
</style>
