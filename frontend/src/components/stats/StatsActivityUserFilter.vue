<template>
  <div ref="root" class="auf">
    <button
      ref="trigger"
      type="button"
      class="auf-trigger"
      aria-haspopup="true"
      :aria-expanded="open"
      @click="open = !open"
    >
      {{ $t('stats.filterUsers') }}
      <span v-if="!allIncluded" class="auf-count">{{ includedCount }}/{{ users.length }}</span>
      <ChevronDown :size="14" class="auf-caret" :class="{ 'auf-caret-open': open }" />
    </button>
    <div v-if="open" class="auf-panel" role="group" :aria-label="$t('stats.filterUsers')">
      <label class="auf-item auf-master">
        <input
          v-indeterminate="someIncluded"
          type="checkbox"
          :checked="allIncluded"
          @change="$emit('set-all', !allIncluded)"
        />
        <span>{{ allIncluded ? $t('stats.filterDeselectAll') : $t('stats.filterSelectAll') }}</span>
      </label>
      <div class="auf-sep" />
      <div class="auf-list">
        <label v-for="u in users" :key="u.id" class="auf-item">
          <input
            type="checkbox"
            :checked="!excludedIds.has(u.id)"
            @change="$emit('toggle', u.id)"
          />
          <span class="auf-name">{{ u.name }}</span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { vIndeterminate } from '@/directives/tableCell'

const props = defineProps({
  users: { type: Array, default: () => [] },
  excludedIds: { type: Object, default: () => new Set() },
})
defineEmits(['toggle', 'set-all'])

const open = ref(false)
const root = ref(null)
const trigger = ref(null)
const includedCount = computed(() => props.users.length - props.excludedIds.size)
const allIncluded = computed(() => props.excludedIds.size === 0)
const someIncluded = computed(
  () => !allIncluded.value && props.excludedIds.size < props.users.length,
)

function onDocClick(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape' && open.value) {
    open.value = false
    trigger.value?.focus()
  }
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.auf {
  position: relative;
}
/* Match the toolbar's per-page <select> (.ctrl-sel) so the filter sits inline. */
.auf-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  font-size: var(--text-xs);
  color: var(--text-primary);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-btn);
  cursor: pointer;
  box-sizing: border-box;
}
@media (hover: hover) {
  .auf-trigger:hover {
    color: var(--text-primary);
  }
}
.auf-trigger:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.auf-count {
  color: var(--accent-400);
  font-variant-numeric: tabular-nums;
}
.auf-caret {
  transition: transform var(--duration-fast);
}
.auf-caret-open {
  transform: rotate(180deg);
}
.auf-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  left: 0;
  min-width: 200px;
  max-height: 280px;
  overflow-y: auto;
  padding: 6px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-dropdown);
}
.auf-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
@media (hover: hover) {
  .auf-item:hover {
    background: var(--surface-3);
  }
}
.auf-master {
  color: var(--text-primary);
  font-weight: var(--font-medium);
}
.auf-sep {
  height: 0.5px;
  margin: 4px 2px;
  background: var(--border-default);
}
.auf-item input {
  width: 15px;
  height: 15px;
  accent-color: var(--accent-500);
  cursor: pointer;
}
.auf-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
