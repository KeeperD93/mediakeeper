<template>
  <div class="pt-hero">
    <Transition name="pt-hero-bg-fade">
      <div :key="viewItem?.id" class="pt-hero-bg" :style="bgStyle" />
    </Transition>

    <div class="pt-hero-vignette" />
    <div class="pt-hero-gradient-bottom" />
    <div class="pt-hero-gradient-left" />

    <div class="pt-hero-content">
      <div v-if="isTv(viewItem)" class="pt-hero-badge">
        {{ $t('portal.hero.series') }}
      </div>

      <h1 class="pt-hero-title" :class="{ 'pt-hero-title--available': viewItem?.emby_url }">
        <span class="pt-hero-title-text">{{ viewItem?.title }}</span>
      </h1>

      <div v-if="isFeatured" class="pt-hero-rank">
        <img src="/assets/icons/emby.svg" alt="Emby" class="pt-hero-rank-emby" />
        {{ $t('portal.hero.featured') }}
      </div>
      <div v-else-if="rank" class="pt-hero-rank">
        <span>🔥</span>
        {{ $t('portal.hero.topRank', { rank }) }}
      </div>

      <p class="pt-hero-overview">{{ viewItem?.overview }}</p>

      <div class="pt-hero-actions">
        <!-- A title on Emby opens there; a missing one surfaces "Request"
             ("Request again" once refused), or a muted "Pending" while a
             request is open. -->
        <a
          v-if="playUrl"
          :href="playUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="pt-hero-btn pt-hero-btn--play"
        >
          <img src="/assets/icons/emby.svg" alt="" class="pt-hero-btn-emby" />
          {{ $t('portal.hero.play') }}
        </a>
        <template v-else-if="!viewItem?.emby_url">
          <button
            v-if="isRequestPending"
            class="pt-hero-btn pt-hero-btn--pending"
            type="button"
            aria-disabled="true"
          >
            <Clock :size="22" :stroke-width="2.5" />
            {{ $t('portal.card.pendingBtn') }}
          </button>
          <button
            v-else
            class="pt-hero-btn pt-hero-btn--play"
            type="button"
            @click="$emit('request', viewItem)"
          >
            <RotateCcw v-if="isRerequest" :size="22" :stroke-width="2.5" />
            <Plus v-else :size="22" :stroke-width="2.5" />
            {{ $t(isRerequest ? 'portal.detail.reRequest' : 'portal.card.requestBtn') }}
          </button>
        </template>
        <button
          v-if="trailer"
          class="pt-hero-btn pt-hero-btn--trailer"
          type="button"
          @click="openLightbox"
        >
          <Video :size="22" />
          {{ $t('portal.detail.watchTrailer') }}
        </button>
        <button
          class="pt-hero-btn pt-hero-btn--info pt-hero-btn--icon"
          type="button"
          :aria-label="$t('portal.moreInfo')"
          @click="$emit('detail', viewItem)"
        >
          <Info :size="24" />
        </button>
      </div>
    </div>

    <TrailerLightbox
      v-if="lightboxOpen && candidates.length"
      :trailers="candidates"
      @close="closeLightbox"
    />

    <!-- The only way to the other titles when the rotation is off
         (reduced motion): real buttons, reachable with the keyboard. -->
    <div v-if="totalItems > 1" class="pt-hero-dots">
      <button
        v-for="i in totalItems"
        :key="i"
        type="button"
        class="pt-hero-dot"
        :aria-label="$t('portal.hero.goTo', { n: i, total: totalItems })"
        :aria-current="currentIndex === i - 1 ? 'true' : undefined"
        @click="$emit('goto', i - 1)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useTrailer } from '@/composables/portal/useTrailer'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { REQUEST_STATUS } from '@/constants/requests'
import TrailerLightbox from './TrailerLightbox.vue'
import { isTv } from '@/constants/media'
import { safeHref } from '@/utils/safeUrl'
import { Clock, Info, Plus, RotateCcw, Video } from 'lucide-vue-next'

import '@/assets/styles/portal/hero-banner.css'

const props = defineProps({
  item: { type: Object, required: true },
  nextItem: { type: Object, default: null },
  currentIndex: { type: Number, default: 0 },
  totalItems: { type: Number, default: 1 },
  rank: { type: Number, default: 0 },
  isFeatured: { type: Boolean, default: false },
})

const emit = defineEmits(['detail', 'goto', 'request', 'trailer-open', 'trailer-close'])

// Trailer-URL resolution only — never mounts a YouTube IFrame in the
// hero itself. Resolving populates ``trailer`` so the trailer button
// can show / hide based on availability; clicking the button
// opens the fullscreen lightbox where the actual <iframe> lives,
// then tears it down on close. Eliminates every chance of the
// YouTube centre play/pause overlay being painted over the hero.
const { trailer, candidates, resolve: resolveTrailer, prefetch: prefetchTrailer } = useTrailer()
const { getStatus, checkStatus } = useRequestStatus()

const lightboxOpen = ref(false)
const viewItem = computed(() => props.item)
const playUrl = computed(() => safeHref(viewItem.value?.emby_url))

// Request status for the current hero item, mirroring the poster cards:
// an active request (pending/approved) swaps the "Request" CTA for a
// muted "Pending" one; a refused one offers "Request again", as its card
// and its page do. Follows the rotation since it derives from ``viewItem``.
const reqStatus = computed(() => {
  const id = viewItem.value?.tmdb_id || viewItem.value?.id
  return id ? getStatus(id) : null
})
const isRequestPending = computed(() => {
  const s = reqStatus.value?.status
  return s === REQUEST_STATUS.PENDING || s === REQUEST_STATUS.APPROVED
})
const isRerequest = computed(() => reqStatus.value?.status === REQUEST_STATUS.REJECTED)

const bgStyle = computed(() => {
  const it = viewItem.value
  const bg = it?.backdrop || it?.poster_url || ''
  return bg ? { backgroundImage: `url(${bg})` } : {}
})

async function ensureTrailerResolved() {
  const it = viewItem.value
  if (!it) return
  await resolveTrailer(it.media_type || 'movie', it.tmdb_id || it.id, it.emby_item_id || null)
}

// Prime the global request-status cache for the current item so the CTA
// can reflect an existing "Pending" request (deduped by TTL in the cache).
function ensureStatusChecked() {
  if (viewItem.value) checkStatus([viewItem.value])
}

function openLightbox() {
  if (!trailer.value) return
  lightboxOpen.value = true
  // Pause the parent hero rotation so the open trailer stays on the
  // chosen title instead of following the carousel to the next item.
  emit('trailer-open')
}
function closeLightbox() {
  lightboxOpen.value = false
  emit('trailer-close')
}

watch(
  () => props.item?.id,
  () => {
    ensureTrailerResolved()
    ensureStatusChecked()
  },
)

// Warm up the next item's trailer URL so the rotation has it ready
// when the user lands on the next slide.
watch(
  () => props.nextItem?.tmdb_id || props.nextItem?.id,
  () => {
    const n = props.nextItem
    if (!n) return
    prefetchTrailer(n.media_type || 'movie', n.tmdb_id || n.id, n.emby_item_id || null)
  },
  { immediate: true },
)

onMounted(() => {
  ensureTrailerResolved()
  ensureStatusChecked()
})
</script>
