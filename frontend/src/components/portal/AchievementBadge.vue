<template>
  <div
    class="pt-badge"
    :class="[`pt-badge--tier-${achievement.tier}`, { 'pt-badge--locked': !unlocked }]"
  >
    <div class="pt-badge-icon">
      <i :class="achievement.icon" />
    </div>
    <div class="pt-badge-info">
      <span class="pt-badge-name">{{ $t(achievement.name_key) }}</span>
      <span class="pt-badge-desc">{{ $t(achievement.description_key) }}</span>
      <div v-if="showProgress && !unlocked" class="pt-badge-bar">
        <div class="pt-badge-fill" :style="{ width: progressPct + '%' }" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  achievement: { type: Object, required: true },
  progress: { type: Number, default: 0 },
  unlocked: { type: Boolean, default: false },
  showProgress: { type: Boolean, default: true },
})

const progressPct = computed(() => {
  const th = props.achievement.threshold || 1
  return Math.min(100, Math.round((props.progress / th) * 100))
})
</script>

<style scoped>
.pt-badge {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem;
  border-radius: var(--radius-card);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  transition: transform var(--portal-dur-base);
}
.pt-badge:hover {
  transform: translateY(-2px);
}
.pt-badge--locked {
  opacity: 0.5;
  filter: grayscale(0.6);
}
.pt-badge-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--portal-radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--portal-text-lg);
  flex-shrink: 0;
}
.pt-badge--tier-1 .pt-badge-icon {
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent);
}
.pt-badge--tier-2 .pt-badge-icon {
  background: rgb(var(--portal-color-success-rgb), 0.15);
  color: var(--portal-color-success);
}
.pt-badge--tier-3 .pt-badge-icon {
  background: rgb(234, 179, 8, 0.15);
  color: #eab308;
}
.pt-badge--tier-4 .pt-badge-icon {
  background: rgb(var(--portal-color-premium-rgb), 0.15);
  color: var(--portal-color-premium);
}
.pt-badge--tier-5 .pt-badge-icon {
  background: rgb(var(--portal-color-error-rgb), 0.15);
  color: var(--portal-color-error);
}
.pt-badge-info {
  flex: 1;
  min-width: 0;
}
.pt-badge-name {
  display: block;
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}
.pt-badge-desc {
  display: block;
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}
.pt-badge-bar {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  margin-top: 0.4rem;
  overflow: hidden;
}
.pt-badge-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width var(--portal-dur-slow) ease;
}
</style>
