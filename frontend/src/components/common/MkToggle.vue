<template>
  <button
    type="button"
    class="mk-toggle"
    :class="{ 'mk-toggle--on': modelValue, 'mk-toggle--disabled': disabled }"
    role="switch"
    :aria-checked="modelValue ? 'true' : 'false'"
    :aria-label="ariaLabel"
    :disabled="disabled"
    @click="toggle"
    @keydown.space.prevent="toggle"
    @keydown.enter.prevent="toggle"
  >
    <span class="mk-toggle__thumb" />
  </button>
</template>

<script setup>
const modelValue = defineModel({ type: Boolean, required: true })

const props = defineProps({
  disabled: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '' },
})

function toggle() {
  if (props.disabled) return
  modelValue.value = !modelValue.value
}
</script>

<style scoped>
.mk-toggle {
  position: relative;
  flex-shrink: 0;
  width: 36px;
  height: 20px;
  padding: 0;
  background: var(--surface-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.mk-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgb(var(--accent-rgb), 0.35);
}

.mk-toggle--on {
  background: var(--accent-500);
  border-color: var(--accent-500);
}

.mk-toggle--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mk-toggle__thumb {
  position: absolute;
  top: 50%;
  left: 1px;
  width: 16px;
  height: 16px;
  background: var(--text-primary);
  border-radius: var(--radius-pill);
  transform: translateY(-50%);
  transition: transform var(--duration-fast) var(--ease-out);
}

.mk-toggle--on .mk-toggle__thumb {
  transform: translate(16px, -50%);
}

@media (prefers-reduced-motion: reduce) {
  .mk-toggle,
  .mk-toggle__thumb {
    transition: none;
  }
}
</style>
