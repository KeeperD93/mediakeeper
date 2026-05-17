<template>
  <div
    class="mk-mediacard"
    :class="{ 'mk-mediacard--fill': fill }"
    :style="{ '--mk-poster-base-w': width }"
    @click="onCardClick"
  >
    <PosterCard
      :title="title"
      :image="image"
      :year="year"
      :duration="duration"
      :status="status"
      :count="count"
      :availability="availability"
      :is-new="isNewOnEmby"
      :blacklisted="isBlacklisted"
      :show-blacklist="isAdmin"
      :rank="rank"
      :tooltip="tooltip"
      @play="onPlay"
      @request="onRequest"
      @toggle-bookmark="onBookmark"
      @toggle-blacklist="onBlacklist"
    />
    <AddToListOverlay :open="addToListOpen" :media="item" @close="addToListOpen = false" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import PosterCard from '@/components/portal/PosterCard.vue'
import AddToListOverlay from '@/components/portal/lists/AddToListOverlay.vue'
import { useMediaCardState } from '@/composables/portal/useMediaCardState'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { REQUEST_STATUS } from '@/constants/requests'
import { USER_ROLE } from '@/constants/auth'
import { formatRuntime } from '@/utils/format'

const props = defineProps({
  item: { type: Object, required: true },
  // Kept for API compatibility with existing callsites — currently a no-op
  // because the PosterCard panel already surfaces title + year on hover.
  showInfo: { type: Boolean, default: false },
  width: { type: String, default: '185px' },
  // Forwarded to PosterCard. Only Top20 cards pass a rank today (1-3).
  rank: { type: Number, default: null },
  // Tells the card to stretch to its grid cell instead of honouring
  // ``width``. Used by the Discover-style pages that drive the column
  // count themselves and need each poster to fill its 1fr track.
  fill: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'request', 'addToList'])

const addToListOpen = ref(false)

const { profile } = usePortalAuth()
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)

const {
  availData,
  reqStatus,
  isRejected,
  retryCount,
  isNewOnEmby,
  displayedReqStatus,
  postitTooltip,
  watchedTooltip,
  reqStatusTooltip,
  newRibbonTooltip,
} = useMediaCardState(props)

const title = computed(() => props.item?.title || '')
const image = computed(() => props.item?.poster_url || props.item?.poster || null)

// Year derivation — items expose either an already-extracted ``year``
// (Top 20, Emby recent, request rows) or a raw release date. We slice
// the first 4 chars so the value lands as the string '2024' regardless
// of the date format (ISO or partial).
const year = computed(() => {
  if (props.item?.year) return String(props.item.year)
  const raw = props.item?.release_date || props.item?.first_air_date || props.item?.date_created
  if (raw && typeof raw === 'string' && raw.length >= 4) return raw.slice(0, 4)
  return ''
})

// Duration label — runtime is in minutes. Items missing the field
// produce an empty string, which the PosterCard meta line elides
// (no orphan ' · ' separator).
const duration = computed(() =>
  formatRuntime(props.item?.runtime || props.item?.duration || 0),
)

const isBlacklisted = computed(() => displayedReqStatus.value === 'blacklisted')

const availability = computed(() => availData.value?.availability || null)

// Single status key for the PosterCard ribbon, picked by priority:
//   1) playback state (in_progress / watched)
//   2) request lifecycle (rejected / pending / approved)
//   3) blacklist flag
// Anything else yields null and PosterCard shows no ribbon.
const status = computed(() => {
  const it = props.item
  if (it?.watch_status === 'in_progress') return 'in_progress'
  if (it?.watched_at && it?.watch_status !== 'in_progress') return 'watched'
  const rs = reqStatus.value?.status
  if (rs === REQUEST_STATUS.REJECTED) return 'rejected'
  if (rs === REQUEST_STATUS.PENDING) return 'pending'
  if (rs === REQUEST_STATUS.APPROVED) return 'approved'
  if (isBlacklisted.value) return 'blacklisted'
  return null
})

const count = computed(() => {
  if (status.value === 'rejected' || status.value === 'pending') {
    return (retryCount.value || 0) + 1
  }
  return 1
})

// Pick the tooltip flavour that matches the active ribbon. The NEW
// ribbon wins over status (PosterCard renders it with `v-if="isNew"`),
// then watch states fall back on the playback date, pending uses the
// postit (requester + date), and admin transitions use the updated /
// requested date.
const tooltip = computed(() => {
  if (isNewOnEmby.value) return newRibbonTooltip.value
  const s = status.value
  if (s === 'watched' || s === 'in_progress') return watchedTooltip.value
  if (s === 'pending') return postitTooltip.value
  if (s === 'approved' || s === 'rejected' || s === 'blacklisted') return reqStatusTooltip.value
  return ''
})

function onCardClick(e) {
  // Ignore clicks that originated from an interactive child (PosterCard
  // buttons or links). Selection only fires when the user clicks the
  // poster artwork itself.
  if (e.target.closest('button, a')) return
  emit('select', props.item)
}

function onPlay() {
  const url = availData.value?.emby_url
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

function onRequest() {
  // Mirror the previous MediaCard rule: a pending / approved request is
  // frozen; only rejected items reach this emit (PosterCard already
  // muted the button for pending / approved cases).
  if (reqStatus.value && !isRejected.value) return
  emit('request', props.item)
}

function onBookmark() {
  addToListOpen.value = true
  emit('addToList', props.item)
}

// TODO post-v1.0 — wire to blacklist endpoint once admin moderation lands.
function onBlacklist() {}
</script>

<style scoped>
.mk-mediacard {
  display: inline-block;
  flex-shrink: 0;
  cursor: pointer;
}

/* PosterCard reads --mk-poster-w from its own scope (where it sets a 185px
   default). Project the caller-provided width into that scope via a deep
   selector so callsites that pass width="220px" keep working. */
.mk-mediacard :deep(.mk-poster) {
  --mk-poster-w: var(--mk-poster-base-w, 185px);
}

/* ``fill`` callers (Discover, Search, Person filmography, Collection)
   manage the column count themselves and want each card to occupy
   100 % of its grid track. Bypass the ``--mk-poster-base-w`` cascade
   on both desktop AND the mobile override below so the poster
   genuinely matches its cell — no centred 108 px island inside a
   wider 1fr track on phones. */
.mk-mediacard--fill {
  display: block;
  width: 100%;
}
.mk-mediacard--fill :deep(.mk-poster) {
  --mk-poster-w: 100%;
}
/* The poster artwork's intrinsic height computation relies on
   ``calc(var(--mk-poster-w) * 1.503)`` — fine when the width is a
   px value but ambiguous when it's a percentage (height % refers to
   the parent height, which is auto inside a grid cell). Forcing the
   2:3 aspect ratio here keeps every poster card identically tall
   regardless of the source image's natural aspect (e.g. a landscape
   16:9 backdrop that TMDB sometimes returns instead of a portrait
   poster) and prevents the ragged-row / phantom-gap effect on the
   search and discover grids. */
.mk-mediacard--fill :deep(.mk-poster__art) {
  height: auto;
  aspect-ratio: 2 / 3;
}

@media (max-width: 767px) {
  /* Match the prior MediaCard mobile clamp so callsite-provided widths
     scale down gracefully on phones (≈65% of the desktop width, with a
     108px floor to keep posters readable). */
  .mk-mediacard :deep(.mk-poster) {
    --mk-poster-w: clamp(108px, 30vw, calc(var(--mk-poster-base-w, 185px) * 0.65));
  }
  .mk-mediacard--fill :deep(.mk-poster) {
    --mk-poster-w: 100%;
  }
}
</style>
