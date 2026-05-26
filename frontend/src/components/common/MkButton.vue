<template>
  <button
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-label="ariaLabel"
    :aria-busy="loading || undefined"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="mk-btn-spinner" aria-hidden="true">
      <MkButtonSpinner :size="iconPx" />
    </span>
    <component
      :is="leftIconComponent"
      v-else-if="leftIconComponent"
      :size="iconPx"
      aria-hidden="true"
      class="mk-btn-icon"
    />
    <span v-if="hasLabel" class="mk-btn-label">
      <slot />
    </span>
    <component
      :is="rightIconComponent"
      v-if="rightIconComponent && !loading"
      :size="iconPx"
      aria-hidden="true"
      class="mk-btn-icon"
    />
  </button>
</template>

<script setup>
import { computed, useSlots } from 'vue'

import { getMkButtonIcon, MkButtonSpinner } from './mkButtonIcons'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: v => ['primary', 'danger', 'success', 'ghost', 'icon', 'link'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg'].includes(v),
  },
  icon: { type: String, default: null },
  iconRight: { type: String, default: null },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  fullwidth: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  ariaLabel: { type: String, default: null },
})

defineEmits(['click'])

const slots = useSlots()
const hasLabel = computed(() => !!slots.default && props.variant !== 'icon')

const leftIconComponent = computed(() => getMkButtonIcon(props.icon))
const rightIconComponent = computed(() => getMkButtonIcon(props.iconRight))

const iconPx = computed(() => {
  if (props.size === 'sm') return 14
  if (props.size === 'lg') return 20
  return 16
})

const classes = computed(() => [
  'mk-btn',
  `mk-btn--${props.variant}`,
  `mk-btn--${props.size}`,
  {
    'mk-btn--fullwidth': props.fullwidth,
    'mk-btn--loading': props.loading,
    'mk-btn--icon-only': props.variant === 'icon' || (!hasLabel.value && props.icon),
  },
])
</script>

<style scoped>
.mk-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-system);
  font-weight: var(--font-medium);
  border-radius: var(--radius-btn);
  border: 1px solid transparent;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition:
    var(--transition-bg), var(--transition-color), var(--transition-border),
    var(--transition-transform);
}

.mk-btn:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.mk-btn:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}

/* ─── Sizes ─── */
.mk-btn--sm {
  height: 28px;
  padding: 0 12px;
  font-size: var(--text-xs);
}
.mk-btn--md {
  height: 36px;
  padding: 0 16px;
  font-size: var(--text-sm);
}
.mk-btn--lg {
  height: 44px;
  padding: 0 24px;
  font-size: var(--text-base);
}

/* Icon-only buttons are square. */
.mk-btn--icon-only {
  padding: 0;
  width: 36px;
}
.mk-btn--icon-only.mk-btn--sm {
  width: 28px;
}
.mk-btn--icon-only.mk-btn--lg {
  width: 44px;
}

/* ─── Variants ─── */
.mk-btn--primary {
  background: var(--accent-500);
  color: var(--color-on-accent);
  box-shadow: var(--shadow-button);
}
@media (hover: hover) {
  .mk-btn--primary:hover:not(:disabled) {
    background: var(--accent-600);
  }
}
.mk-btn--primary:active:not(:disabled) {
  background: var(--accent-700);
}

.mk-btn--danger {
  background: var(--color-error);
  color: var(--color-on-accent);
  box-shadow: var(--shadow-button);
}
@media (hover: hover) {
  .mk-btn--danger:hover:not(:disabled) {
    background: var(--color-error-strong);
  }
}

.mk-btn--success {
  background: var(--color-success);
  color: var(--color-on-accent);
  box-shadow: var(--shadow-button);
}
@media (hover: hover) {
  .mk-btn--success:hover:not(:disabled) {
    background: var(--color-success-light);
  }
}

.mk-btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-ghost);
  border-width: 1.5px;
}
@media (hover: hover) {
  .mk-btn--ghost:hover:not(:disabled) {
    background: var(--surface-1);
    color: var(--text-primary);
    border-color: var(--border-ghost-hover);
  }
}

.mk-btn--icon {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-ghost);
  border-width: 1.5px;
}
@media (hover: hover) {
  .mk-btn--icon:hover:not(:disabled) {
    background: var(--surface-1);
    color: var(--text-primary);
    border-color: var(--border-ghost-hover);
  }
}

.mk-btn--link {
  background: transparent;
  color: var(--text-muted);
  padding: 0 12px;
}
@media (hover: hover) {
  .mk-btn--link:hover:not(:disabled) {
    color: var(--text-primary);
  }
}

/* ─── Modifiers ─── */
.mk-btn--fullwidth {
  width: 100%;
}

.mk-btn--loading .mk-btn-label {
  opacity: 0.8;
}

.mk-btn-spinner {
  display: inline-flex;
  animation: mk-btn-spin 0.8s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .mk-btn-spinner {
    animation: none;
  }
}

@keyframes mk-btn-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
