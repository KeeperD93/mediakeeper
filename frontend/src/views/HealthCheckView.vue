<template>
  <div ref="rootRef" class="cinema-health mk-page-root">
    <!-- ═══ Progress bar ═══ -->
    <div v-if="scanStatus.running" class="hc-progress-wrap">
      <div class="hc-progress-bar">
        <div class="hc-progress-fill" :style="{ width: progressPct + '%' }" />
      </div>
      <span class="hc-progress-text">
        {{ scanStatus.progress }} / {{ scanStatus.total }} — {{ scanStatus.current_item }}
      </span>
    </div>

    <!-- ═══ Health tab ═══ -->
    <div v-show="tab === 'health'" class="tab-panel">
      <div class="hc-header">
        <span v-if="summary && summary.last_scan" class="hc-last-scan">
          {{ $t('healthCheck.lastScan') }} {{ formatAgo(summary.last_scan) }}
        </span>
        <button class="hc-scan-btn" :disabled="scanStatus.running" @click="startScan">
          <RefreshCw v-if="!scanStatus.running" :size="13" />
          <span v-else class="mk-spin mk-spin-14" />
          {{ scanStatus.running ? $t('healthCheck.scanning') : $t('healthCheck.scanNow') }}
        </button>
      </div>

      <!-- Score + Severity -->
      <div v-if="summary" class="hc-hero-row">
        <div class="hc-score-card glass-card">
          <svg viewBox="0 0 120 120" class="hc-score-ring">
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              stroke-width="8"
            />
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              :style="{ stroke: scoreColor }"
              stroke-width="8"
              stroke-linecap="round"
              :stroke-dasharray="scoreCircum"
              :stroke-dashoffset="scoreOffset"
              transform="rotate(-90 60 60)"
              class="hc-score-arc"
            />
          </svg>
          <div class="hc-score-center">
            <span class="hc-score-num" :style="{ color: scoreColor }">{{ summary.score }}</span>
            <span class="hc-score-label">{{ $t('healthCheck.scoreLabel') }}</span>
          </div>
        </div>

        <div class="hc-severity-col">
          <div
            class="glass-card hc-sev-card"
            :class="{ 'hc-sev-active': filterSev === 'critical' }"
            @click="toggleSeverity('critical')"
          >
            <span class="hc-sev-dot hc-sev-dot-critical" />
            <div class="hc-sev-text">
              <span class="hc-sev-count hc-sev-count-critical">{{ summary.critical }}</span>
              <span class="hc-sev-label">{{ $t('healthCheck.critical') }}</span>
            </div>
          </div>
          <div
            class="glass-card hc-sev-card"
            :class="{ 'hc-sev-active': filterSev === 'warning' }"
            @click="toggleSeverity('warning')"
          >
            <span class="hc-sev-dot hc-sev-dot-warning" />
            <div class="hc-sev-text">
              <span class="hc-sev-count hc-sev-count-warning">{{ summary.warning }}</span>
              <span class="hc-sev-label">{{ $t('healthCheck.warning') }}</span>
            </div>
          </div>
          <div
            class="glass-card hc-sev-card"
            :class="{ 'hc-sev-active': filterSev === 'info' }"
            @click="toggleSeverity('info')"
          >
            <span class="hc-sev-dot hc-sev-dot-info" />
            <div class="hc-sev-text">
              <span class="hc-sev-count hc-sev-count-info">{{ summary.info }}</span>
              <span class="hc-sev-label">{{ $t('healthCheck.info') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- By library + By type -->
      <div v-if="summary" class="hc-breakdown-row">
        <div v-if="filteredLibraries.length" class="glass-card hc-breakdown-card">
          <h3 class="hc-section-title">{{ $t('healthCheck.byLibrary') }}</h3>
          <div class="hc-lib-list">
            <div
              v-for="[lib, count] in filteredLibraries"
              :key="lib"
              class="hc-lib-item"
              :class="{ 'hc-lib-active': filterLib === lib }"
              @click="toggleLibrary(lib)"
            >
              <div class="hc-lib-row">
                <span class="hc-lib-name">{{ lib }}</span>
                <span class="hc-lib-count">{{ count }}</span>
              </div>
              <div class="hc-lib-bar">
                <div class="hc-lib-bar-fill" :style="{ width: libPct(count) + '%' }" />
              </div>
            </div>
          </div>
        </div>
        <div v-if="Object.keys(summary.by_type || {}).length" class="glass-card hc-breakdown-card">
          <h3 class="hc-section-title">{{ $t('healthCheck.byType') }}</h3>
          <div class="hc-types-wrap">
            <div
              v-for="(count, typ) in summary.by_type"
              :key="typ"
              class="hc-type-chip"
              :class="{ 'hc-type-active': filterTyp === typ }"
              @click="toggleType(typ)"
            >
              <span class="hc-type-dot" :class="'hc-td-' + typ" />
              <span class="hc-type-label">{{ $t('healthCheck.issues.' + typ) }}</span>
              <span class="hc-type-count">{{ count }}</span>
            </div>
          </div>
          <template v-if="Object.keys(summary.by_extension || {}).length">
            <h3 class="hc-section-title hc-section-title-spaced">
              {{ $t('healthCheck.byExtension') }}
            </h3>
            <div class="hc-types-wrap">
              <div
                v-for="(count, ext) in summary.by_extension"
                :key="ext"
                class="hc-type-chip hc-ext-chip"
                :class="{ 'hc-type-active': filterExt === ext }"
                @click="toggleExt(ext)"
              >
                <span class="hc-type-dot hc-td-ext" />
                <span class="hc-type-label">.{{ ext }}</span>
                <span class="hc-type-count">{{ count }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- No scan yet -->
      <div v-if="!summary && !loading" class="hc-empty glass-card">
        <ShieldCheck class="hc-empty-icon" :size="48" :stroke-width="1.5" />
        <span>{{ $t('healthCheck.noScanYet') }}</span>
      </div>

      <!-- Issues list -->
      <div v-if="summary && summary.total_issues > 0" class="glass-card hc-issues-card">
        <div class="hc-issues-header">
          <h3 class="hc-section-title">
            {{ $t('healthCheck.detectedIssues') }}
            <span class="hc-issues-total">({{ issues.total }})</span>
          </h3>
          <div class="hc-filters">
            <select v-model="filterSev" class="hc-select mk-select-chevron" @change="reloadAll()">
              <option value="">{{ $t('common.all') }} — {{ $t('healthCheck.severity') }}</option>
              <option value="critical">{{ $t('healthCheck.critical') }}</option>
              <option value="warning">{{ $t('healthCheck.warning') }}</option>
              <option value="info">{{ $t('healthCheck.info') }}</option>
            </select>
            <select
              v-if="libOptions.length"
              v-model="filterLib"
              class="hc-select mk-select-chevron"
              @change="reloadAll()"
            >
              <option value="">{{ $t('healthCheck.allLibraries') }}</option>
              <option v-for="l in libOptions" :key="l" :value="l">{{ l }}</option>
            </select>
          </div>
        </div>

        <template v-if="groupedPosters.length">
          <div class="hc-poster-grid">
            <div
              v-for="item in groupedPosters"
              :key="item.key"
              class="sg-card"
              @click="selectedIssue = item"
            >
              <div class="sg-poster-wrap">
                <img
                  :src="`/api/emby/image/${item.item_id}?type=Primary`"
                  :alt="item.title"
                  class="sg-poster"
                  loading="lazy"
                  @error="e => (e.target.style.display = 'none')"
                />
                <div class="sg-gradient" />
                <span class="sg-tag hc-sg-tag" :class="'hc-sg-' + item.severity">
                  {{ item.issue_count }}
                </span>
                <div class="sg-bottom">
                  <div class="sg-title">{{ item.title }}</div>
                  <div v-if="item.library" class="sg-episode">{{ item.library }}</div>
                </div>
              </div>
            </div>
          </div>

          <HealthCheckIssueOverlay :item="selectedIssue" @close="selectedIssue = null" />

          <div ref="sentinelRef" class="hc-sentinel">
            <div v-if="loadingMore" class="hc-loading-more">
              <span class="mk-spin mk-spin-16" />
            </div>
          </div>
        </template>

        <MkEmptyState v-else :icon="Search" size="sm" :title="$t('healthCheck.noResults')" />
      </div>
    </div>

    <!-- ═══ Config tab ═══ -->
    <div v-show="tab === 'config'" class="tab-panel">
      <HealthCheckConfig />
    </div>

    <!-- ═══ Scroll to top ═══ -->
    <Transition name="hc-scroll-up">
      <button
        v-if="showScrollTop && tab === 'health'"
        class="hc-scroll-top"
        @click="scrollToTop"
      >
        <ChevronUp :size="14" :stroke-width="2.5" />
        {{ $t('healthCheck.backToTop') }}
      </button>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useHealthCheck } from '@/composables/useHealthCheck'
import { useTabSync } from '@/composables/useTabSync'
import HealthCheckConfig from '@/components/healthcheck/HealthCheckConfig.vue'
import HealthCheckIssueOverlay from '@/components/healthcheck/HealthCheckIssueOverlay.vue'
import { ChevronUp, RefreshCw, Search, ShieldCheck } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import '@/assets/styles/healthcheck-view.css'

const {
  summary,
  issues,
  groupedPosters,
  scanStatus,
  loading,
  loadingMore,
  filterSev,
  filterLib,
  filterTyp,
  filterExt,
  scoreColor,
  scoreCircum,
  scoreOffset,
  progressPct,
  libOptions,
  filteredLibraries,
  libPct,
  loadSummary,
  loadGroupedPosters,
  reloadIssues,
  loadMore,
  startScan,
  pollStatus,
  startPolling,
  stopPolling,
  reloadAll,
  toggleSeverity,
  toggleLibrary,
  toggleType,
  toggleExt,
  formatAgo,
} = useHealthCheck()

const tab = useTabSync(['health', 'config'], 'health')
const selectedIssue = ref(null)

// Scroll to top
const rootRef = ref(null)
const showScrollTop = ref(false)
let scrollContainer = null

function getScrollContainer(el) {
  let node = el
  while (node && node !== document.body) {
    const style = getComputedStyle(node)
    if (style.overflowY === 'scroll' || style.overflowY === 'auto') return node
    node = node.parentElement
  }
  return window
}
function onScroll() {
  if (scrollContainer && scrollContainer !== window) {
    showScrollTop.value = scrollContainer.scrollTop > 400
  } else {
    showScrollTop.value = window.scrollY > 400
  }
}
function scrollToTop() {
  if (scrollContainer && scrollContainer !== window) {
    scrollContainer.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// Infinite scroll
const sentinelRef = ref(null)
let observer = null

function setupObserver() {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    entries => {
      if (entries[0]?.isIntersecting && issues.value.has_more && !loadingMore.value) {
        loadMore()
      }
    },
    { rootMargin: '200px' },
  )
  nextTick(() => {
    if (sentinelRef.value) observer.observe(sentinelRef.value)
  })
}

watch(
  () => issues.value.items?.length,
  () => {
    nextTick(() => {
      if (sentinelRef.value && observer) observer.observe(sentinelRef.value)
    })
  },
)

onMounted(async () => {
  nextTick(() => {
    scrollContainer = rootRef.value ? getScrollContainer(rootRef.value) : window
    scrollContainer.addEventListener('scroll', onScroll)
  })
  await Promise.all([loadSummary(), reloadIssues(), loadGroupedPosters(), pollStatus()])
  loading.value = false
  if (scanStatus.value.running) startPolling()
  setupObserver()
})

onUnmounted(() => {
  stopPolling()
  if (observer) observer.disconnect()
  if (scrollContainer) scrollContainer.removeEventListener('scroll', onScroll)
})
</script>
