<template>
  <span class="lb-me-pill">{{ $t('portal.leaderboard.myRank.label') }}</span>
</template>

<style scoped>
.lb-me-pill {
  flex-shrink: 0;
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-bold);
  line-height: var(--portal-lh-compact);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  padding: 0 var(--portal-space-1);
  border-radius: var(--portal-radius-pill);
  background: var(--portal-accent-500);
  color: var(--portal-text-primary);
}
</style>
