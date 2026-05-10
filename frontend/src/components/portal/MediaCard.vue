<template>
  <div
    class="pt-card"
    :style="{ '--pt-card-w': width }"
    @click="$emit('select', item)"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="pt-card-poster">
      <img
        v-if="item.poster_url || item.poster"
        :src="item.poster_url || item.poster"
        :alt="item.title"
        class="pt-card-img"
        loading="lazy"
        @error="imgError = true"
      />
      <div v-if="imgError || (!item.poster_url && !item.poster)" class="pt-card-placeholder">
        <Film :size="28" :stroke-width="1.5" :opacity="0.3" />
      </div>

      <!-- Status dot (top right) — availability signal only:
             green  = fully available on Emby
             orange = partially available
           Requested items use a bronze tag instead (see below). -->
      <span
        v-if="statusDot"
        class="pt-status-dot"
        :class="`pt-status-dot--${statusDot.variant}`"
        :title="statusDot.tooltip"
      />

      <!-- "Requested" bronze tag (top right) — replaces the old blue dot
           for requested items. Same flag shape as the "New" ribbon
           but mirrored (flush to the right edge). Only shows when the
           item has an active request AND is not already available. -->
      <span v-if="showRequestedTag" class="pt-requested-tag" :title="postitTooltip">
        {{ $t('portal.card.requestedTag') }}
      </span>

      <!-- "New on Emby" ribbon -->
      <span v-if="isNewOnEmby" class="pt-new-ribbon" :title="newRibbonTooltip">
        {{ $t('portal.card.newRibbon') }}
      </span>

      <!-- Watched-status tag — the profile "Recent plays" carousel
           stamps ``watched_at`` + ``watch_status`` on each item so we
           can flag films/series as either "In progress" (indigo) or
           "Already watched" (slate). Everything with a watched_at gets a tag;
           old data without a status defaults to "watched". -->
      <span
        v-if="item.watched_at"
        class="pt-watched-tag"
        :class="`pt-watched-tag--${item.watch_status === 'in_progress' ? 'in-progress' : 'watched'}`"
        :title="watchedTooltip"
      >
        {{
          $t(
            item.watch_status === 'in_progress'
              ? 'portal.card.inProgressTag'
              : 'portal.card.watchedTag',
          )
        }}
      </span>

      <!-- Request status tags — shown when either the profile carousel
           stamps ``_request_status`` directly, OR the global request
           cache carries a status for this tmdb_id (so the home grid
           also flags rejected / approved / available titles). -->
      <span
        v-if="displayedReqStatus && !showRequestedTag && !isNewOnEmby && !item.watched_at"
        class="pt-req-status-tag"
        :class="`pt-req-status-tag--${displayedReqStatus}`"
        :title="reqStatusTooltip"
      >
        {{ requestStatusLabel }}
        <span
          v-if="retryCount >= 1"
          class="pt-req-retry-badge"
          :title="$t('portal.card.retryBadgeTooltip', { count: retryCount + 1 })"
        >
          x{{ retryCount + 1 }}
        </span>
      </span>

      <!-- Hover overlay -->
      <div class="pt-card-hover" :class="{ visible: hovered }">
        <div class="pt-card-hover-info">
          <div class="pt-card-hover-top">
            <span v-if="item.vote" class="pt-card-vote">★ {{ item.vote }}</span>
            <span v-if="item.year" class="pt-card-year">{{ item.year }}</span>
          </div>
          <div class="pt-card-hover-title">{{ item.title }}</div>
        </div>

        <!-- Add-to-list button — floats bottom-right above the CTA.
             Parent decides what happens on click (opens a list
             picker modal, etc.). -->
        <button
          type="button"
          class="pt-card-list-btn"
          :aria-label="$t('portal.card.addToListBtn')"
          :title="$t('portal.card.addToListBtn')"
          @click.stop="onAddToListClick"
        >
          <ListPlus :size="18" :stroke-width="2.2" />
        </button>

        <!-- Available: "Lancer" button with the Emby logo, same look as
             the hero CTAs. -->
        <a
          v-if="availData?.emby_url"
          class="pt-card-request-btn pt-card-watch-btn"
          :href="availData.emby_url"
          target="_blank"
          @click.stop
        >
          <span class="pt-card-request-icon pt-card-watch-icon">
            <img src="/assets/icons/emby.svg" alt="" class="pt-card-emby-logo" />
          </span>
          <span class="pt-card-request-text">{{ $t('portal.card.launchBtn') }}</span>
          <span class="pt-card-request-shine" />
        </a>

        <!-- Not available: "Demander" button — disabled when an active
             request already exists for this tmdb_id (global rule:
             one request per item, regardless of who filed it).
             Rejected requests bypass the lock: the user can resubmit
             right from the card with a dedicated "Re-demander" label. -->
        <button
          v-else
          class="pt-card-request-btn"
          :class="{
            'pt-card-request-btn--disabled': !!reqStatus && !canResubmit,
            'pt-card-request-btn--resubmit': canResubmit,
          }"
          :disabled="!!reqStatus && !canResubmit"
          :title="
            reqStatus && !canResubmit
              ? postitTooltip
              : isRejected && reqStatus?.reject_reason
                ? reqStatus.reject_reason
                : ''
          "
          @click.stop="onRequestClick"
        >
          <span class="pt-card-request-icon">
            <RefreshCw v-if="canResubmit" :size="14" :stroke-width="2.5" />
            <Plus v-else-if="!reqStatus" :size="14" :stroke-width="2.5" />
            <Check v-else :size="14" :stroke-width="2.5" />
          </span>
          <span class="pt-card-request-text">
            {{
              canResubmit
                ? $t('portal.card.resubmitBtn')
                : reqStatus
                  ? $t('portal.card.requestedBtn')
                  : $t('portal.card.requestBtn')
            }}
          </span>
          <span class="pt-card-request-shine" />
        </button>
      </div>
    </div>

    <AddToListOverlay :open="addToListOpen" :media="item" @close="addToListOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaCardState } from '@/composables/portal/useMediaCardState'
import AddToListOverlay from '@/components/portal/lists/AddToListOverlay.vue'
import { Check, Film, ListPlus, Plus, RefreshCw } from 'lucide-vue-next'
import { REQUEST_STATUS } from '@/constants/requests'

import '@/assets/styles/portal/media-card-base.css'
import '@/assets/styles/portal/media-card-hover.css'

const props = defineProps({
  item: { type: Object, required: true },
  showInfo: { type: Boolean, default: false },
  width: { type: String, default: '185px' },
})

const emit = defineEmits(['select', 'request', 'addToList'])
const { t, locale } = useI18n()
const hovered = ref(false)
const imgError = ref(false)
const addToListOpen = ref(false)

const watchedTooltip = computed(() => {
  if (!props.item.watched_at) return ''
  const d = new Date(props.item.watched_at)
  if (Number.isNaN(d.getTime())) return ''
  const date = d.toLocaleDateString(locale.value, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  return props.item.watch_status === 'in_progress'
    ? t('portal.card.inProgressTooltip', { date })
    : t('portal.card.watchedTooltip', { date })
})

// Which status string to render on the sash. Prefers the explicit
// ``_request_status`` stamped by the profile carousel; falls back to
// the global request cache so the home / discover grids also show
// the rejected / approved / available sash.
const displayedReqStatus = computed(
  () => props.item?._request_status || reqStatus.value?.status || null,
)

// Tooltip for the request-status sash (profile carousel). Falls back
// to a plain status label when no date / reason is available so the
// sash always surfaces something on hover.
const reqStatusTooltip = computed(() => {
  const r = reqStatus.value
  if (!r) return requestStatusLabel.value
  if (r.status === REQUEST_STATUS.REJECTED && r.reject_reason) return r.reject_reason
  let when = ''
  if (r.requested_at) {
    try {
      when = new Date(r.requested_at).toLocaleDateString(locale.value, {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    } catch {
      /**/
    }
  }
  const label = requestStatusLabel.value
  return when ? `${label} — ${when}` : label
})

const {
  availData,
  reqStatus,
  isRejected,
  canResubmit,
  retryCount,
  postitTooltip,
  isNewOnEmby,
  newRibbonTooltip,
  statusDot,
  showRequestedTag,
  requestStatusLabel,
} = useMediaCardState(props)

function onRequestClick() {
  // Rejected requests can be resubmitted — everything else with an
  // active request is frozen (admin owns the transition).
  if (reqStatus.value && !canResubmit.value) return
  emit('request', props.item)
}

function onAddToListClick() {
  // Open the list picker locally so the button works out of the box
  // wherever MediaCard is used. Parents can still observe via @addToList.
  addToListOpen.value = true
  emit('addToList', props.item)
}
</script>
