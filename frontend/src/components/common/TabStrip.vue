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
          <span v-if="tab.badge != null && tab.badge !== 0" class="mk-tab-corner-badge">
            {{ tab.badge }}
          </span>
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
  placement: { type: String, default: 'top', validator: v => ['top', 'bottom-mobile'].includes(v) },
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
  background: rgb(255, 255, 255, 0.03);
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
  color: #fff;
}
.mk-tab-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mk-tab-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
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
  background: rgb(255, 255, 255, 0.08);
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

/* Corner badge — hidden by default, shown only in bottom-mobile mode on mobile */
.mk-tab-corner-badge {
  display: none;
}

/* Placement: top (default) — sticky top of the page scroll container */
.mk-tabs-placement-top {
  position: sticky;
  top: 0;
  z-index: 10;
  margin-bottom: 24px;
}

/* Placement: bottom-mobile — sticky top on desktop, fixed bottom on mobile (Portal-style).
 * On mobile the tabs float fixed at the bottom; `.mk-app-content` in main.css adds
 * a matching padding-bottom so page content isn't hidden behind them. */
.mk-tabs-placement-bottom-mobile {
  position: sticky;
  top: 0;
  z-index: 10;
  margin-bottom: 24px;
}

@media (max-width: 767px) {
  .mk-tabs-placement-bottom-mobile {
    position: fixed;
    inset: auto 0 0;
    margin: 0;
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-bottom: none;
    border-top: 1px solid var(--border-strong);
    background: rgb(var(--bg-primary-rgb), 0.9);
    backdrop-filter: blur(20px) saturate(1.2);
    -webkit-backdrop-filter: blur(20px) saturate(1.2);
    box-shadow: 0 -10px 30px rgb(0, 0, 0, 0.35);
    padding: 0.35rem 0.25rem calc(0.35rem + env(safe-area-inset-bottom, 0px));
    z-index: 95;
  }

  .mk-tabs-placement-bottom-mobile .mk-tabs {
    gap: 0.1rem;
    max-width: 640px;
    margin: 0 auto;
    overflow-x: visible;
    justify-content: space-around;
  }

  .mk-tabs-placement-bottom-mobile .mk-tab {
    flex-direction: column;
    gap: 2px;
    min-height: 52px;
    padding: 6px 8px;
    font-size: var(--text-3xs);
    font-weight: var(--font-medium);
    letter-spacing: var(--tracking-wide);
    color: rgb(255, 255, 255, 0.58);
    border-radius: var(--radius-input);
    background: transparent;
    transition:
      background var(--duration-base) ease,
      color var(--duration-base) ease,
      box-shadow var(--duration-base) ease;
  }
  .mk-tabs-placement-bottom-mobile .mk-tab.active {
    color: #fff;
    background: linear-gradient(135deg, rgb(var(--accent-rgb), 0.28), rgb(var(--accent-rgb), 0.12));
    box-shadow: inset 0 0 0 1px rgb(var(--accent-rgb), 0.32);
  }
  .mk-tabs-placement-bottom-mobile .mk-tab:active:not(.mk-tab-disabled) {
    transform: scale(0.94);
  }

  .mk-tabs-placement-bottom-mobile .mk-tab-icon-wrap {
    width: 28px;
    height: 28px;
  }
  .mk-tabs-placement-bottom-mobile .mk-tab-icon {
    width: 22px;
    height: 22px;
    stroke-width: 2;
  }

  /* Swap inline badge for corner badge on icon */
  .mk-tabs-placement-bottom-mobile .mk-tab-badge {
    display: none;
  }
  .mk-tabs-placement-bottom-mobile .mk-tab-corner-badge {
    display: inline-block;
    position: absolute;
    top: -3px;
    right: -4px;
    min-width: 14px;
    height: 14px;
    padding: 0 3px;
    border-radius: var(--radius-pill);
    background: #ef4444;
    color: #fff;
    font-size: 0.58rem;
    font-weight: var(--font-bold);
    line-height: 14px;
    text-align: center;
    box-shadow: 0 0 0 2px rgb(var(--bg-primary-rgb), 0.9);
  }

  .mk-tabs-placement-bottom-mobile .mk-tab-label {
    max-width: 100%;
    line-height: 1.1;
  }
}
</style>
