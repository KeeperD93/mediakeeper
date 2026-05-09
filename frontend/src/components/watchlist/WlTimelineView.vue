<template>
  <div ref="rootRef" class="tl">
    <div v-if="timelineLoading" class="tl-empty"><div class="tl-spin" /></div>
    <div v-else-if="!entries.length" class="tl-empty">
      <p class="tl-empty-text">{{ $t('watchlist.noEpisodesOnPeriod') }}</p>
    </div>
    <template v-else>
      <div class="tl-outer">
        <!-- Scrollable timeline -->
        <div ref="scrollRef" class="tl-scroll">
          <TlRow
            v-for="(e, i) in entries"
            :key="e.date"
            :entry="e"
            :left-active="isLeft(i)"
          />
        </div>

        <TlNavSidebar
          :months="months"
          @go-today="goToday"
          @go-month="goMonth"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, onActivated, nextTick, watch } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import { useTimelineNav } from './WlTimelineView/useTimelineNav'
import TlRow from './WlTimelineView/TlRow.vue'
import TlNavSidebar from './WlTimelineView/TlNavSidebar.vue'

const { timelineItems, timelineLoading } = useWatchlist()
const rootRef = ref(null)

const { scrollRef, entries, months, goToday, goMonth, doAutoScroll } =
  useTimelineNav(timelineItems)

const isMobile = ref(false)
function updateIsMobile() {
  isMobile.value = typeof window !== 'undefined' && window.innerWidth < 768
}

// Auto-scroll au first affichage
onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  nextTick(() => doAutoScroll(rootRef))
})
onUnmounted(() => {
  window.removeEventListener('resize', updateIsMobile)
})
onActivated(() => {
  goToday()
})

// Scroll to today as soon as data arrives (first load)
watch(timelineLoading, v => {
  if (!v) nextTick(() => doAutoScroll(rootRef))
})

function isLeft(i) {
  return !isMobile.value && i % 2 === 0
}
</script>

<style scoped>
.tl {
  min-height: 300px;
}
.tl-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
}
.tl-empty-text {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.tl-spin {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--accent-500);
  border-radius: 50%;
  animation: sp 0.8s linear infinite;
}
@keyframes sp {
  to {
    transform: rotate(360deg);
  }
}

.tl-outer {
  display: flex;
  align-items: stretch;
}
.tl-scroll {
  flex: 1;
  min-width: 0;
  max-height: 80vh;
  overflow: hidden auto;
  padding: 20px 0 60px;
  scrollbar-width: thin;
  scrollbar-color: rgb(99, 102, 241, 0.2) transparent;
}
</style>
