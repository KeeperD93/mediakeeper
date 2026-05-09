<template>
  <div class="ale-side-block">
    <button
      type="button"
      class="ale-history-toggle"
      :aria-expanded="historyOpen"
      @click="$emit('update:historyOpen', !historyOpen)"
    >
      <span class="ale-history-toggle-label">{{ $t('portal.lists.history.title') }}</span>
      <span v-if="history.length" class="ale-history-toggle-count">{{ history.length }}</span>
      <ChevronDown
        class="ale-history-toggle-chev"
        :class="{ 'ale-history-toggle-chev--open': historyOpen }"
        :size="14"
        :stroke-width="2.4"
      />
    </button>
    <template v-if="historyOpen">
      <div v-if="loadingHistory" class="ale-loading"><MkSpinner size="md" /></div>
      <ul v-else-if="history.length" class="ale-history">
        <li v-for="h in history" :key="h.id" class="ale-event">
          <span v-if="h.username" class="ale-event-who">{{ h.username }}</span>
          <span class="ale-event-action" :class="`ale-event--${h.action}`">
            {{ actionLabel(h) }}
          </span>
          <span class="ale-event-date">{{ formatDate(h.created_at) }}</span>
        </li>
      </ul>
      <p v-else class="ale-empty">—</p>
    </template>
  </div>
</template>

<script setup>
import { ChevronDown } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'

defineProps({
  history: { type: Array, required: true },
  historyOpen: { type: Boolean, required: true },
  loadingHistory: { type: Boolean, default: false },
  actionLabel: { type: Function, required: true },
  formatDate: { type: Function, required: true },
})
defineEmits(['update:historyOpen'])
</script>

<style scoped>
.ale-side-block {
  margin-bottom: 16px;
}
.ale-loading {
  display: flex;
  justify-content: center;
  padding: 18px;
}
.ale-empty {
  color: rgb(255, 255, 255, 0.3);
  font-size: var(--portal-text-xs);
  padding: 12px 0;
  text-align: center;
}
.ale-history {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ale-event {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  font-size: var(--portal-text-2xs);
}
.ale-event-action {
  font-weight: var(--portal-font-extrabold);
  font-size: var(--portal-text-4xs);
  padding: 2px 7px;
  border-radius: var(--portal-radius-xs);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  background: var(--portal-surface-3);
  color: var(--portal-text-body-muted);
}
.ale-event--added {
  background: rgb(74, 222, 128, 0.14);
  color: var(--portal-color-success-soft);
}
.ale-event--removed {
  background: rgb(248, 113, 113, 0.14);
  color: var(--portal-color-error-soft);
}
.ale-event--copied {
  background: rgb(34, 211, 238, 0.14);
  color: #67e8f9;
}
.ale-event--created {
  background: rgb(var(--portal-color-premium-rgb), 0.14);
  color: var(--portal-color-premium-soft);
}
.ale-event--deleted {
  background: rgb(var(--portal-color-error-rgb), 0.16);
  color: var(--portal-color-error-soft);
}
.ale-event-who {
  color: var(--portal-text-body-muted);
  font-weight: var(--portal-font-bold);
}
.ale-event-date {
  color: rgb(255, 255, 255, 0.35);
  margin-left: auto;
  font-size: var(--portal-text-2xs);
}

.ale-history-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  margin-bottom: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  font: inherit;
  text-align: left;
  -webkit-tap-highlight-color: transparent;
}
.ale-history-toggle-label {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-black);
  color: rgb(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.ale-history-toggle-count {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-bold);
  color: rgb(255, 255, 255, 0.45);
  padding: 1px 7px;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
}
.ale-history-toggle-chev {
  color: rgb(255, 255, 255, 0.45);
  margin-left: auto;
  transition: transform 180ms ease;
}
.ale-history-toggle-chev--open {
  transform: rotate(180deg);
}
@media (hover: hover) {
  .ale-history-toggle:hover .ale-history-toggle-label,
  .ale-history-toggle:hover .ale-history-toggle-chev {
    color: rgb(255, 255, 255, 0.8);
  }
}
</style>
