<template>
  <div class="pt-skeleton" :style="{ width }">
    <div class="pt-skeleton-poster">
      <div class="pt-shimmer" />
    </div>
    <div v-if="showInfo" class="pt-skeleton-info">
      <div class="pt-skeleton-line pt-shimmer pt-skeleton-line--title" />
      <div class="pt-skeleton-line pt-shimmer pt-skeleton-line--sub" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  width: { type: String, default: '160px' },
  showInfo: { type: Boolean, default: true },
})
</script>

<style scoped>
.pt-skeleton { flex-shrink: 0; }
.pt-skeleton-poster {
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: var(--radius-card);
  background: var(--bg-tertiary);
  overflow: hidden;
  position: relative;
}
.pt-skeleton-info { padding: 0.5rem 0.2rem 0; }
.pt-skeleton-line { border-radius: var(--portal-radius-xs); background: var(--bg-tertiary); position: relative; overflow: hidden; }
.pt-skeleton-line--title { width: 80%; height: 12px; }
.pt-skeleton-line--sub   { width: 40%; height: 10px; margin-top: 6px; }

.pt-shimmer {
  position: relative;
  overflow: hidden;
}
.pt-shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--portal-surface-2) 50%,
    transparent 100%
  );
  animation: pt-shimmer-wave 1.5s infinite;
}

@keyframes pt-shimmer-wave {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
</style>
