<template>
  <span
    v-if="count > 0"
    class="lb-trophies"
    :class="{ 'lb-trophies--large': large }"
    role="img"
    :title="$t('portal.leaderboard.trophiesWon', { n: count }, count)"
    :aria-label="$t('portal.leaderboard.trophiesWon', { n: count }, count)"
  >
    <Trophy class="lb-trophies-icon" :size="12" :stroke-width="2.5" aria-hidden="true" />
    +{{ count }}
  </span>
</template>

<script setup>
import { Trophy } from 'lucide-vue-next'

defineProps({
  count: { type: Number, default: 0 },
  // Next to the lead of the first place, which it must match in size.
  large: { type: Boolean, default: false },
})
</script>

<style scoped>
.lb-trophies {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: var(--portal-radius-pill);
  background: rgb(var(--portal-color-warning-rgb), 0.18);
  color: var(--portal-color-warning);
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-bold);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.lb-trophies--large {
  padding: 2px 8px;
}
@media (min-width: 640px) {
  .lb-trophies--large {
    gap: 6px;
    padding: 4px 12px;
    font-size: var(--portal-text-xs);
  }
  .lb-trophies--large .lb-trophies-icon {
    width: 14px;
    height: 14px;
  }
}
</style>
