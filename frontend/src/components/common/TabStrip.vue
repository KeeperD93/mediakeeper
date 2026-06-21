<template>
  <div class="mk-tabs-wrap" :class="'mk-tabs-placement-' + placement" role="tablist">
    <div class="mk-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="mk-tab"
        :class="{ active: modelValue === tab.id, 'mk-tab-disabled': tab.disabled }"
        :disabled="tab.disabled"
        role="tab"
        :aria-selected="modelValue === tab.id"
        :title="tab.label"
        @click="select(tab)"
      >
        <span class="mk-tab-icon-wrap">
          <component
            :is="tab.icon"
            v-if="tab.icon"
            class="mk-tab-icon"
            :size="iconSize"
            :stroke-width="1.8"
          />
        </span>
        <span class="mk-tab-label">{{ tab.label }}</span>
        <span
          v-if="tab.badge != null"
          class="mk-tab-badge"
          :class="tab.badgeVariant ? 'mk-tab-badge-' + tab.badgeVariant : ''"
        >
          {{ tab.badge }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: [String, Number], required: true },
  tabs: { type: Array, required: true },
  placement: { type: String, default: 'top', validator: v => v === 'top' },
  iconSize: { type: Number, default: 15 },
})
const emit = defineEmits(['update:modelValue'])

function select(tab) {
  if (tab.disabled) return
  emit('update:modelValue', tab.id)
}
</script>

<style scoped>
.mk-tabs-wrap {
  display: flex;
  background: var(--surface-1);
  backdrop-filter: var(--blur-sm);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 3px;
}
.mk-tabs {
  display: flex;
  gap: 2px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.mk-tabs::-webkit-scrollbar {
  display: none;
}

.mk-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 10px;
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  color: rgb(255, 255, 255, 0.35);
  border: none;
  background: transparent;
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition:
    background var(--duration-base),
    color var(--duration-base);
  font-family: inherit;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .mk-tab:hover:not(.mk-tab-disabled) {
    color: rgb(255, 255, 255, 0.6);
  }
}
.mk-tab.active {
  background: var(--surface-3);
  color: var(--text-primary);
}
.mk-tab-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mk-tab-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.mk-tab-icon {
  flex-shrink: 0;
}
.mk-tab-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mk-tab-badge {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  padding: 1px 6px;
  border-radius: var(--radius-btn);
  background: var(--surface-3);
  color: var(--text-faint);
  flex-shrink: 0;
}
.mk-tab.active .mk-tab-badge {
  background: rgb(var(--accent-rgb), 0.2);
  color: var(--accent-300);
}
.mk-tab-badge-danger {
  background: rgb(244, 63, 94, 0.15);
  color: #fb7185;
}
.mk-tab.active .mk-tab-badge-danger {
  background: rgb(var(--accent-rgb), 0.2);
  color: var(--accent-300);
}
.mk-tab-badge-warn {
  background: rgb(var(--color-warning-rgb), 0.15);
  color: var(--color-warning);
}
.mk-tab.active .mk-tab-badge-warn {
  background: rgb(var(--accent-rgb), 0.2);
  color: var(--accent-300);
}

/* Placement: top (default) — sticky top of the page scroll container.
   Mobile-first: tabs use equal flex distribution with tight padding and
   small font so all labels fit on a 360–414px viewport. Labels that
   exceed their cell get ellipsified rather than escaping the cell. */
.mk-tabs-placement-top {
  position: sticky;
  top: 0;
  z-index: 10;
  margin-bottom: 24px;
  padding: 4px;
}
.mk-tabs-placement-top .mk-tabs {
  gap: 4px;
  overflow-y: visible;
  padding-bottom: 2px;
}
.mk-tabs-placement-top .mk-tab {
  flex: 1 1 0;
  min-width: 0;
  min-height: 44px;
  padding: 6px 6px 10px;
  font-size: var(--text-xs);
  line-height: 1.6;
  gap: 3px;
}
.mk-tabs-placement-top .mk-tab-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.6;
  padding-bottom: 1px;
}
@media (min-width: 768px) {
  .mk-tabs-placement-top {
    padding: 3px;
  }
  .mk-tabs-placement-top .mk-tabs {
    gap: 2px;
    overflow-y: auto;
    padding-bottom: 0;
  }
  .mk-tabs-placement-top .mk-tab {
    min-height: 0;
    padding: 9px 10px;
    font-size: var(--text-sm);
    line-height: normal;
    gap: 6px;
  }
  .mk-tabs-placement-top .mk-tab-label {
    line-height: normal;
    padding-bottom: 0;
  }
}
</style>
