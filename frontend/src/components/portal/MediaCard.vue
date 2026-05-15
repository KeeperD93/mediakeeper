<template>
  <div class="mk-mediacard" :style="{ '--mk-poster-base-w': width }" @click="onCardClick">
    <PosterCard
      :title="title"
      :image="image"
      :year="year"
      :status="status"
      :count="count"
      :availability="availability"
      :is-new="isNewOnEmby"
      :blacklisted="isBlacklisted"
      :show-blacklist="isAdmin"
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

const props = defineProps({
  item: { type: Object, required: true },
  // Kept for API compatibility with existing callsites — currently a no-op
  // because the PosterCard panel already surfaces title + year on hover.
  showInfo: { type: Boolean, default: false },
  width: { type: String, default: '185px' },
})

const emit = defineEmits(['select', 'request', 'addToList'])

const addToListOpen = ref(false)

const { profile } = usePortalAuth()
const isAdmin = computed(() => profile.value?.role === USER_ROLE.ADMIN)

const { availData, reqStatus, isRejected, retryCount, isNewOnEmby, displayedReqStatus } =
  useMediaCardState(props)

const title = computed(() => props.item?.title || '')
const image = computed(() => props.item?.poster_url || props.item?.poster || null)

const year = computed(() => {
  if (props.item?.year) return props.item.year
  const raw = props.item?.release_date
  if (!raw) return ''
  const y = new Date(raw).getFullYear()
  return Number.isFinite(y) ? y : ''
})

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

@media (max-width: 767px) {
  /* Match the prior MediaCard mobile clamp so callsite-provided widths
     scale down gracefully on phones (≈65% of the desktop width, with a
     108px floor to keep posters readable). */
  .mk-mediacard :deep(.mk-poster) {
    --mk-poster-w: clamp(108px, 30vw, calc(var(--mk-poster-base-w, 185px) * 0.65));
  }
}
</style>
