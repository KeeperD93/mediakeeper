<template>
  <span class="lb-me-pill">{{ $t('portal.leaderboard.myRank.label') }}</span>
</template>

<style scoped>
.lb-me-pill {
  flex-shrink: 0;
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-widest);
  padding: 2px 6px;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-accent-500);
  color: var(--portal-text-primary);
}
</style>
