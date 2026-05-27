<template>
  <div class="cinema-stats mk-page-root">
    <div class="stats-content">
      <KeepAlive>
        <component :is="currentTabComponent" />
      </KeepAlive>

      <StatsUserProfilePopover />
      <StatsMergeModal />
      <StatsHoverPreview />
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'StatsView' })
import { computed, defineAsyncComponent, onDeactivated, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'
const StatsGeneralTab = defineAsyncComponent(() => import('@/components/stats/StatsGeneralTab.vue'))
const StatsUsersTab = defineAsyncComponent(() => import('@/components/stats/StatsUsersTab.vue'))
const StatsActivityTab = defineAsyncComponent(
  () => import('@/components/stats/StatsActivityTab.vue'),
)
const StatsChartsTab = defineAsyncComponent(() => import('@/components/stats/StatsChartsTab.vue'))
const StatsToolsTab = defineAsyncComponent(() => import('@/components/stats/StatsToolsTab.vue'))
import StatsUserProfilePopover from '@/components/stats/StatsUserProfilePopover.vue'
import StatsMergeModal from '@/components/stats/StatsMergeModal.vue'
import StatsHoverPreview from '@/components/stats/StatsHoverPreview.vue'
import '@/assets/styles/stats-view.css'

const { startSessionPolling, stopSessionPolling } = useStats()
const { activeTab, profileOpen, mergeModal } = useStatsUI()

const TAB_IDS = ['general', 'users', 'activity', 'charts', 'tools']
const DEFAULT_TAB = 'general'
const route = useRoute()
const router = useRouter()

const TAB_COMPONENTS = {
  general: StatsGeneralTab,
  users: StatsUsersTab,
  activity: StatsActivityTab,
  charts: StatsChartsTab,
  tools: StatsToolsTab,
}
const currentTabComponent = computed(
  () => TAB_COMPONENTS[activeTab.value] || TAB_COMPONENTS[DEFAULT_TAB],
)

// URL → activeTab (handles deep-links and sidebar sub-link clicks)
watch(
  () => route.query.tab,
  q => {
    const next = TAB_IDS.includes(q) ? q : DEFAULT_TAB
    if (next !== activeTab.value) activeTab.value = next
  },
  { immediate: true },
)

// activeTab → URL (handles in-view jumps like goToActivitySearch())
watch(activeTab, tab => {
  if (route.path !== '/stats') return
  if (route.query.tab === tab) return
  router.replace({ path: '/stats', query: { ...route.query, tab } })
})

onMounted(() => {
  startSessionPolling()
})
onUnmounted(() => {
  stopSessionPolling()
})

// Close stats overlays (merge modal + user profile popup) when the
// user navigates away. Both states live module-level in useStatsUI
// so without this hook the overlay survives module switches and
// reappears stacked on the wrong tab when the user returns to /stats.
// Pattern identical to the ``selected.clear()`` hook in
// StatsUsersTab.vue:446-448 for bulk checkbox selection.
onDeactivated(() => {
  mergeModal.open = false
  profileOpen.value = false
})
</script>
