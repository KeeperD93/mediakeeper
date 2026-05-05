<template>
  <div class="pt-search-page">
    <header class="pt-search-head">
      <button class="pt-search-back" :aria-label="$t('common.back')" @click="$router.back()">
        <ChevronLeft :size="20" :stroke-width="2.5" />
      </button>

      <div class="pt-search-copy">
        <span class="pt-search-kicker">{{ $t('portal.search.title') }}</span>
        <h1 class="pt-search-title">
          {{ query ? $t('portal.search.resultsTitle', { query }) : $t('portal.search.emptyTitle') }}
        </h1>
        <p class="pt-search-subtitle">
          {{ query ? $t('portal.search.resultsSubtitle') : $t('portal.search.emptyPrompt') }}
        </p>
      </div>
    </header>

    <div v-if="!query" class="pt-search-state">
      {{ $t('portal.search.emptyPrompt') }}
    </div>

    <template v-else>
      <div class="pt-search-grid">
        <MediaCard
          v-for="item in items"
          :key="`${item.media_type || 'movie'}-${item.tmdb_id || item.id}`"
          :item="item"
          @select="openDetail(item)"
          @request="requestItem = item"
        />
      </div>

      <div v-if="loading && !items.length" class="pt-search-state">
        <MkSpinner size="sm" inline />
        {{ $t('common.loading') }}
      </div>

      <div v-else-if="!loading && !items.length" class="pt-search-state">
        {{ $t('portal.search.emptyResults', { query }) }}
      </div>

      <div v-if="loading && items.length" class="pt-search-state pt-search-state--tail">
        <MkSpinner size="sm" inline />
        {{ $t('common.loading') }}
      </div>

      <div v-if="hasMore" ref="sentinelRef" class="pt-search-sentinel" />
      <div v-else-if="items.length" class="pt-search-state pt-search-state--tail">
        {{ $t('portal.discover.endOfList') }}
      </div>
    </template>

    <RequestModal
      v-if="requestItem"
      :item="requestItem"
      :is-admin="isAdmin"
      @close="requestItem = null"
      @done="onRequestDone"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import MediaCard from '@/components/portal/MediaCard.vue'
import RequestModal from '@/components/portal/RequestModal.vue'
import { ChevronLeft } from 'lucide-vue-next'
import { USER_ROLE } from '@/constants/auth'
import MkSpinner from '@/components/common/MkSpinner.vue'

import '@/assets/styles/portal/search-results.css'

const route = useRoute()
const router = useRouter()
const { apiGet } = useApi()
const { checkAvailability } = useAvailability()
const { checkStatus, markRequested } = useRequestStatus()
const { profile } = usePortalAuth()

const items = ref([])
const loading = ref(false)
const hasMore = ref(false)
const page = ref(0)
const requestItem = ref(null)
const sentinelRef = ref(null)

const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)
const query = computed(() => {
  if (typeof route.query.q !== 'string') return ''
  return route.query.q.trim()
})

const seen = new Set()
let observer = null
let activeToken = 0

function reset() {
  items.value = []
  loading.value = false
  hasMore.value = false
  page.value = 0
  seen.clear()
  activeToken += 1
}

function isElementInViewport(el) {
  if (!el) return false
  const rect = el.getBoundingClientRect()
  return rect.top < (window.innerHeight || document.documentElement.clientHeight) + 220
}

async function loadMore() {
  if (loading.value || !query.value) return
  if (page.value > 0 && !hasMore.value) return

  loading.value = true
  const token = activeToken

  try {
    const nextPage = page.value + 1
    const res = await apiGet(
      `/api/portal/catalog/search?q=${encodeURIComponent(query.value)}&page=${nextPage}`,
    )
    if (token !== activeToken) return

    const batch = Array.isArray(res?.items) ? res.items : []
    const fresh = batch.filter(item => {
      const key = `${item.media_type || 'movie'}:${item.tmdb_id || item.id}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })

    items.value.push(...fresh)
    page.value = nextPage
    hasMore.value = batch.length >= 20 && nextPage < 5

    if (fresh.length) {
      await Promise.all([checkAvailability(fresh), checkStatus(fresh)])
    }
  } catch {
    if (token === activeToken) {
      hasMore.value = false
    }
  } finally {
    if (token === activeToken) {
      loading.value = false
      if (hasMore.value && isElementInViewport(sentinelRef.value)) {
        requestAnimationFrame(() => loadMore())
      }
    }
  }
}

function observe(el) {
  if (!el) return
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          loadMore()
        }
      }
    },
    { rootMargin: '220px 0px' },
  )
  observer.observe(el)
}

function openDetail(item) {
  router.push({
    name: 'portal-media-detail',
    params: {
      type: item.media_type || 'movie',
      id: item.tmdb_id || item.id,
    },
  })
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

watch(sentinelRef, el => {
  if (el) observe(el)
})

watch(
  query,
  async () => {
    reset()
    if (!query.value) return
    hasMore.value = true
    await loadMore()
    await nextTick()
    if (sentinelRef.value) observe(sentinelRef.value)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})
</script>
