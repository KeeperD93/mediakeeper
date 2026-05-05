<template>
  <div class="sub-cov-row">
    <span class="sub-cov-label">{{ label }}</span>
    <div class="sub-cov-bar">
      <div class="sub-cov-fill" :style="{ width: percentage + '%', background: color }" />
    </div>
    <span class="sub-cov-pct">{{ percentage }}%</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  percentage: { type: Number, default: 0 },
})

const color = computed(() => {
  if (props.percentage >= 90) return 'var(--color-success)'
  if (props.percentage >= 50) return 'var(--color-warning)'
  return 'var(--color-error)'
})
</script>

<style scoped>
.sub-cov-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sub-cov-label {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--text-muted);
  min-width: 30px;
}
.sub-cov-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--surface-3);
  overflow: hidden;
}
.sub-cov-fill {
  height: 100%;
  border-radius: 3px;
  transition: width var(--duration-slower);
}
.sub-cov-pct {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  min-width: 36px;
  text-align: right;
}
</style>
