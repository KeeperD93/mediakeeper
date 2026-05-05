<template>
  <!--
    Generic infinite-scroll discover page.

    Powers both the category routes (/portal/category/:type) and
    the watch-provider routes (/portal/platform/:slug). The route
    component decides which API endpoint to hit and which title to
    show, then this component handles fetching, sorting, infinite
    scroll, and rendering a uniform poster grid.
  -->
  <div class="vd">
    <header class="dmd-header">
      <button class="dmd-back" :aria-label="$t('common.back')" @click="$router.back()">
        <ChevronLeft :size="20" :stroke-width="2.5" />
      </button>
      <h1 class="dmd-title">{{ title }}</h1>
      <div v-if="!hideSort" class="dmd-sort">
        <button
          v-for="opt in SORT_OPTIONS"
          :key="opt.key"
          class="dmd-sort-btn"
          :class="{ 'dmd-sort-btn--active': sort === opt.key }"
          @click="setSort(opt.key)"
        >
          {{ $t(opt.label) }}
        </button>
      </div>
    </header>

    <div class="dmd-grid">
      <MediaCard
        v-for="item in items"
        :key="`${item.media_type}-${item.tmdb_id || item.id}`"
        :item="item"
        @select="onSelect(item)"
        @request="onRequest(item)"
      />
    </div>

    <div v-if="loading" class="dmd-loading">
      <MkSpinner size="sm" inline />
      {{ $t('common.loading') }}
    </div>

    <div v-if="isEmpty" class="dmd-empty">{{ $t('portal.discover.empty') }}</div>

    <!-- Sentinel element observed by IntersectionObserver. -->
    <div v-if="hasMore" ref="sentinelRef" class="dmd-sentinel" />
    <div v-else-if="items.length" class="dmd-end">{{ $t('portal.discover.endOfList') }}</div>

    <RequestModal
      v-if="requestItem"
      :item="requestItem"
      :is-admin="false"
      @close="requestItem = null"
      @done="onRequestDone"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import MediaCard from '@/components/portal/MediaCard.vue'
import RequestModal from '@/components/portal/RequestModal.vue'
import { useInfiniteDiscover } from '@/composables/portal/useInfiniteDiscover'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { ChevronLeft } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'

const props = defineProps({
  /** Display title shown in the header. */
  title: { type: String, required: true },
  /** Backend endpoint (without page/sort, the composable appends them). */
  endpoint: { type: String, required: true },
  /**
   * Hide the sort toggle pill. Defaults to true: the browse pages
   * accessible from the Portal home always sort by popularity
   * desc and offer no user-facing sort options. Set to false only
   * if a future page explicitly needs sort controls.
   */
  hideSort: { type: Boolean, default: true },
})

const router = useRouter()
const sentinelRef = ref(null)
const requestItem = ref(null)
const { markRequested } = useRequestStatus()

const SORT_OPTIONS = [
  { key: 'popularity', label: 'portal.discover.sort.popularity' },
  { key: 'release', label: 'portal.discover.sort.release' },
  { key: 'rating', label: 'portal.discover.sort.rating' },
]

const { items, loading, hasMore, sort, setSort, loadMore, observe, reset, isEmpty } =
  useInfiniteDiscover(props.endpoint)

function onSelect(item) {
  const type = item.media_type || 'movie'
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

function onRequest(item) {
  requestItem.value = item
}

function onRequestDone(payload) {
  if (requestItem.value) {
    markRequested(requestItem.value.tmdb_id || requestItem.value.id, {
      retry_count: payload?.retry_count || 0,
      request_id: payload?.id || null,
    })
  }
  requestItem.value = null
}

onMounted(async () => {
  await loadMore()
  await nextTick()
  observe(sentinelRef.value)
})

// Re-wire the observer if the sentinel is re-rendered after a sort change
// (because hasMore briefly toggled false).
watch(sentinelRef, el => {
  if (el) observe(el)
})

// Reset & reload entirely when the parent route changes the endpoint
// (going from one category page to another without unmount).
watch(
  () => props.endpoint,
  () => {
    reset()
    loadMore()
  },
)
</script>

<style scoped>
.vd {
  min-height: 100vh;
  padding: 5rem 4% 4rem;
  background: var(--bg-primary);
  color: #fff;
}
.dmd-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.dmd-back {
  background: var(--portal-surface-3);
  border: 1px solid var(--portal-border-strong);
  color: #fff;
  width: 40px;
  height: 40px;
  border-radius: var(--portal-radius-circle);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.dmd-back:hover {
  background: rgb(255, 255, 255, 0.14);
}

.dmd-title {
  font-size: clamp(1.4rem, 2.5vw + 0.5rem, 2.2rem);
  font-weight: var(--portal-font-black);
  flex: 1;
  min-width: 0;
}
.dmd-sort {
  display: inline-flex;
  gap: 0.4rem;
  background: rgb(255, 255, 255, 0.05);
  border: 1px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--portal-radius-pill);
  padding: 4px;
}
.dmd-sort-btn {
  padding: 0.4rem 0.9rem;
  background: transparent;
  border: none;
  color: rgb(255, 255, 255, 0.65);
  cursor: pointer;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  border-radius: var(--portal-radius-pill);
  transition:
    background var(--portal-dur-fast),
    color var(--portal-dur-fast);
}
.dmd-sort-btn:hover {
  color: #fff;
}
.dmd-sort-btn--active {
  background: var(--accent, #4338ca);
  color: #fff;
}

.dmd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
@media (min-width: 1024px) {
  .dmd-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  }
}

.dmd-loading,
.dmd-end,
.dmd-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 2rem 1rem;
  color: rgb(255, 255, 255, 0.5);
  font-size: var(--portal-text-sm);
}

.dmd-sentinel {
  height: 1px;
  width: 100%;
}
</style>
