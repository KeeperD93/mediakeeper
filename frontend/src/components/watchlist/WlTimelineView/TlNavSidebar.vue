<template>
  <div class="tl-nav">
    <div class="tl-nav-list">
      <button class="tl-nav-item tl-nav-auj" @click="$emit('go-today')">
        <span class="tl-nav-dot" aria-hidden="true" />
        {{ $t('watchlist.todayShort') }}
      </button>
      <div class="tl-nav-line" />
      <button
        v-for="m in months"
        :key="m.k"
        class="tl-nav-item"
        :class="{ now: m.now }"
        @click="$emit('go-month', m.first)"
      >
        {{ m.s }}
        <span class="tl-nav-y">{{ m.y }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({ months: { type: Array, required: true } })
defineEmits(['go-today', 'go-month'])
</script>

<style scoped>
.tl-nav {
  width: 84px;
  flex-shrink: 0;
  border-left: 0.5px solid var(--border-default);
}
.tl-nav-list {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 6px 0;
  /* Mobile: fixed-height band that stays visible while the page scrolls. */
  height: 80vh;
  justify-content: center;
}
@media (min-width: 768px) {
  /* Desktop: the timeline panel now fills the content area (see WatchlistView
     .wl-fill + WlTimelineView .tl), so the months bar follows that height. */
  .tl-nav-list {
    height: 100%;
  }
}
.tl-nav-auj {
  background: rgb(99, 102, 241, 0.15) !important;
  color: var(--accent-400) !important;
  border-radius: var(--radius-btn) !important;
  padding: 6px 4px !important;
  gap: 2px;
  font-size: 0.56rem !important;
  font-weight: var(--font-extrabold) !important;
}
.tl-nav-auj:hover {
  background: rgb(99, 102, 241, 0.25) !important;
}
.tl-nav-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.tl-nav-line {
  width: 28px;
  height: 1px;
  background: var(--surface-3);
  margin: 4px 0;
}
.tl-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 7px 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-weight: var(--font-bold);
  font-family: inherit;
  text-transform: uppercase;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition:
    background-color var(--duration-fast),
    color var(--duration-fast);
  width: 72px;
  font-size: var(--text-2xs);
}
.tl-nav-item:hover {
  background: rgb(99, 102, 241, 0.1);
  color: var(--accent-300);
}
.tl-nav-item.now {
  background: rgb(99, 102, 241, 0.22);
  color: var(--text-primary);
  font-weight: var(--font-extrabold);
  box-shadow: inset 2px 0 0 rgb(99, 102, 241);
}
.tl-nav-y {
  font-size: var(--text-3xs);
  opacity: 0.8;
}

@media (max-width: 767px) {
  .tl-nav {
    width: 40px;
  }
  .tl-nav-item {
    width: 36px;
    padding: 4px 2px;
    font-size: 0.52rem;
  }
  .tl-nav-y {
    display: none;
  }
}
</style>
