<template>
  <div v-if="totalPages > 1" class="sp-pagination">
    <button class="sp-btn" :disabled="currentPage <= 1" @click="emit('go-to', currentPage - 1)">
      <ChevronLeft :size="14" />
    </button>
    <button
      v-for="p in visiblePages"
      :key="p"
      class="sp-btn"
      :class="{ active: p === currentPage, dots: p === '...' }"
      :disabled="p === '...'"
      @click="p !== '...' && emit('go-to', p)"
    >
      {{ p }}
    </button>
    <button
      class="sp-btn"
      :disabled="currentPage >= totalPages"
      @click="emit('go-to', currentPage + 1)"
    >
      <ChevronRight :size="14" />
    </button>
    <span class="sp-info">{{ libraryTotal }} {{ $t('subtitles.results') }}</span>
  </div>
</template>

<script setup>
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

defineProps({
  currentPage: { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  visiblePages: { type: Array, default: () => [] },
  libraryTotal: { type: Number, default: 0 },
})
const emit = defineEmits(['go-to'])
</script>

<style scoped>
.sp-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 16px 0 8px;
}
.sp-btn {
  min-width: 34px;
  height: 34px;
  border-radius: var(--radius-btn);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--duration-base);
  border: 1px solid var(--border-default);
  background: rgb(255, 255, 255, 0.02);
  color: var(--text-faint);
}
.sp-btn:hover:not(:disabled, .dots) {
  background: var(--surface-3);
  color: var(--text-primary);
}
.sp-btn.active {
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  border-color: rgb(var(--accent-rgb), 0.3);
}
.sp-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.sp-btn.dots {
  border: none;
  background: none;
  cursor: default;
  color: rgb(255, 255, 255, 0.2);
}
.sp-info {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin-left: 12px;
}
</style>
