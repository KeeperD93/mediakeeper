<template>
  <div class="cinema-wl mk-page-root">
    <!-- Mesh background identical to Dashboard/Stats -->

    <div class="wl-inner">
      <div v-if="loading && !data" class="wl-center">
        <MkSpinner size="md" />
      </div>

      <div v-else-if="!data || (!data.scan_time && !data.series?.length)" class="wl-center">
        <ClipboardCheck class="wl-empty-icon" :size="48" :stroke-width="1.5" />
        <p class="wl-empty-text">{{ $t('watchlist.noScan') }}</p>
        <button class="wl-scan-btn" :disabled="loading" @click="refreshScan">
          <RefreshCw :size="14" />
          {{ $t('watchlist.startScan') }}
        </button>
      </div>

      <template v-else>
        <div v-show="activeTab === 'missing'" class="tab-panel">
          <WlSeriesView type="missing" @scan="refreshScan" />
        </div>
        <div v-if="mounted.timeline" v-show="activeTab === 'timeline'" class="tab-panel">
          <WlTimelineView />
        </div>
        <div v-show="activeTab === 'suivi'" class="tab-panel"><WlSuiviView /></div>
        <div v-if="mounted.calendar" v-show="activeTab === 'calendar'" class="tab-panel">
          <WlCalendarView />
        </div>
        <div v-show="activeTab === 'ignored'" class="tab-panel"><WlIgnoredView /></div>
      </template>
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'WatchlistView' })
import { reactive, watch, onMounted, defineAsyncComponent } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import { useTabSync } from '@/composables/useTabSync'
const WlSeriesView = defineAsyncComponent(() => import('@/components/watchlist/WlSeriesView.vue'))
const WlTimelineView = defineAsyncComponent(
  () => import('@/components/watchlist/WlTimelineView.vue'),
)
const WlSuiviView = defineAsyncComponent(() => import('@/components/watchlist/WlSuiviView.vue'))
const WlCalendarView = defineAsyncComponent(
  () => import('@/components/watchlist/WlCalendarView.vue'),
)
const WlIgnoredView = defineAsyncComponent(() => import('@/components/watchlist/WlIgnoredView.vue'))
import { ClipboardCheck, RefreshCw } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'

const { data, loading, loadIgnored, loadTracked, loadScan, refreshScan, prefetchCalendar } =
  useWatchlist()
const activeTab = useTabSync(['missing', 'timeline', 'suivi', 'calendar', 'ignored'], 'missing')

// Lazy mount: only mount heavy tabs on first selection
const mounted = reactive({ timeline: false, calendar: false })
watch(
  activeTab,
  tab => {
    if (tab === 'timeline') mounted.timeline = true
    if (tab === 'calendar') mounted.calendar = true
  },
  { immediate: true },
)

onMounted(async () => {
  await Promise.all([loadIgnored(), loadTracked()])
  loadScan()
  prefetchCalendar() // populates calCache + timelineItems in the background
})
</script>

<style scoped>
.cinema-wl {
  position: relative;
  min-height: 100%;
  padding: 12px 24px 24px;
  /* §2.9 : `clip` au lieu de `hidden` — `hidden` aurait promu la racine en
     scroll container et bloqué le scroll vertical du document. `clip`
     empêche le débordement horizontal sans créer de contexte de scroll. */
  overflow-x: clip;
}
.wl-inner {
  position: relative;
  z-index: 1;
}
.tab-panel {
  animation: tab-in 0.25s ease;
}
@keyframes tab-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.wl-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  gap: 16px;
}
.wl-scan-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: var(--radius-card);
  background: var(--accent-600);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.wl-empty-icon {
  opacity: 0.2;
  color: var(--text-muted);
}
.wl-empty-text {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
@media (max-width: 767px) {
  .cinema-wl {
    padding: 0 16px 16px;
  }
}
</style>
