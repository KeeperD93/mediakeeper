<template>
  <div
    class="lb-period-tabs"
    role="tablist"
    :aria-label="$t('portal.leaderboard.periodsLabel')"
    @keydown="onKeydown"
  >
    <button
      v-for="option in LEADERBOARD_PERIODS"
      :id="`${baseId}-tab-${option}`"
      :key="option"
      type="button"
      role="tab"
      class="lb-period-tab"
      :class="{ 'lb-period-tab--on': option === period }"
      :aria-selected="option === period"
      :aria-controls="`${baseId}-panel`"
      :tabindex="option === period ? 0 : -1"
      @click="period = option"
    >
      {{ $t(`portal.leaderboard.periods.${option}`) }}
    </button>
  </div>
</template>

<script setup>
import { LEADERBOARD_PERIODS } from '@/constants/leaderboard'

defineProps({
  // The panel these tabs control has the id `${baseId}-panel`.
  baseId: { type: String, required: true },
})

const period = defineModel({ type: String, required: true })

function onKeydown(event) {
  if (event.altKey || event.ctrlKey || event.metaKey) return
  const last = LEADERBOARD_PERIODS.length - 1
  const current = LEADERBOARD_PERIODS.indexOf(period.value)
  const next = {
    ArrowRight: current === last ? 0 : current + 1,
    ArrowLeft: current === 0 ? last : current - 1,
    Home: 0,
    End: last,
  }[event.key]
  if (next === undefined) return
  event.preventDefault()
  period.value = LEADERBOARD_PERIODS[next]
  event.currentTarget.children[next].focus()
}
</script>

<style scoped>
.lb-period-tabs {
  display: flex;
  flex-wrap: wrap;
  /* This gap between two lines keeps their touch bands apart. */
  gap: var(--portal-space-3-5) clamp(var(--portal-space-1), 2vw, var(--portal-space-2));
}
.lb-period-tab {
  position: relative;
  padding: var(--portal-space-1-5)
    clamp(var(--portal-space-1), 3.5vw - var(--portal-space-1), var(--portal-space-3-5));
  font-family: inherit;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  white-space: nowrap;
  color: var(--portal-text-body-muted);
  background: var(--portal-surface-2);
  border: var(--portal-border-width) solid var(--portal-border-default);
  cursor: pointer;
  transition:
    color var(--portal-dur-fast) var(--portal-ease-default),
    background-color var(--portal-dur-fast) var(--portal-ease-default);
  -webkit-tap-highlight-color: transparent;
}
.lb-period-tab::after {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: var(--portal-touch-target);
  transform: translateY(-50%);
}
.lb-period-tab--on {
  color: var(--portal-text-primary);
  font-weight: var(--portal-font-bold);
  background: var(--portal-gradient-accent);
  border-color: transparent;
  box-shadow: var(--portal-shadow-pill);
}
.lb-period-tab:focus-visible {
  outline: var(--portal-focus-ring);
  outline-offset: var(--portal-focus-ring-offset);
}
@media (hover: hover) {
  .lb-period-tab:not(.lb-period-tab--on):hover {
    color: var(--portal-text-primary);
    background: var(--portal-surface-3);
  }
}
@media (min-width: 768px) {
  .lb-period-tab::after {
    content: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .lb-period-tab {
    transition: none;
  }
}
</style>
