<template>
  <div class="mk-poster">
    <div class="mk-poster__art">
      <slot name="poster">
        <img v-if="image" :src="image" :alt="title" />
        <div v-else class="mk-poster__placeholder">{{ title }}</div>
      </slot>

      <PremiumRibbon
        v-if="isNew"
        :label="$t('portal.posterCard.badgeNew')"
        bg="var(--portal-color-success)"
        pulse
      />
      <PremiumRibbon
        v-else-if="statusColor"
        :label="statusLabel"
        :count="count"
        :bg="statusColor"
      />

      <div
        v-if="availability"
        class="mk-poster__avail"
        :class="`mk-poster__avail--${availability}`"
      >
        <span class="mk-poster__avail-dot" />
        {{ availability === 'full' ? $t('portal.posterCard.availFull') : $t('portal.posterCard.availPartial') }}
      </div>

      <div class="mk-poster__panel">
        <div class="mk-poster__title" :title="title">{{ title }}</div>
        <div class="mk-poster__meta">{{ year }} · {{ duration }}</div>

        <div class="mk-poster__actions">
          <button
            type="button"
            class="mk-btn"
            :class="`mk-btn--${action.tone}`"
            :disabled="action.tone === 'muted'"
            @click="handlePrimaryAction"
          >
            <img
              v-if="action.tone === 'play'"
              src="/assets/icons/emby.svg"
              alt=""
              class="mk-btn__emby"
              width="15"
              height="15"
            />
            <RotateCcw v-else-if="action.icon === 'rotate'" :size="14" :stroke-width="2" />
            <Clock v-else-if="action.icon === 'clock'" :size="14" :stroke-width="2" />
            <Plus v-else :size="14" :stroke-width="2" />
            {{ action.label }}
          </button>

          <button
            type="button"
            class="mk-iconbtn"
            :class="{ 'mk-iconbtn--gold': bookmarked }"
            :title="$t('portal.posterCard.btnBookmark')"
            :aria-label="$t('portal.posterCard.btnBookmark')"
            @click="emit('toggle-bookmark')"
          >
            <Bookmark v-if="!bookmarked" :size="14" :stroke-width="2" />
            <Bookmark v-else :size="14" :stroke-width="2" fill="currentColor" />
          </button>

          <button
            type="button"
            class="mk-iconbtn"
            :class="{ 'mk-iconbtn--red': blacklisted || status === 'blacklisted' }"
            :title="$t('portal.posterCard.btnBlacklist')"
            :aria-label="$t('portal.posterCard.btnBlacklist')"
            @click="emit('toggle-blacklist')"
          >
            <EyeOff :size="14" :stroke-width="2" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bookmark, EyeOff, Plus, Clock, RotateCcw } from 'lucide-vue-next'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'

import '@/assets/styles/portal/poster-card.css'

const props = defineProps({
  title: { type: String, required: true },
  image: { type: String, default: null },
  year: { type: [String, Number], default: '' },
  duration: { type: String, default: '' },
  // REST-aligned keys — mirror the request lifecycle + watch status used
  // across the portal API. Null = no status decoration.
  status: {
    type: String,
    default: null,
    validator: v =>
      v == null ||
      ['pending', 'approved', 'rejected', 'blacklisted', 'watched', 'in_progress'].includes(v),
  },
  count: { type: Number, default: 1 },
  availability: {
    type: String,
    default: null,
    validator: v => v == null || v === 'full' || v === 'partial',
  },
  isNew: { type: Boolean, default: false },
  bookmarked: { type: Boolean, default: false },
  blacklisted: { type: Boolean, default: false },
})

const emit = defineEmits(['play', 'request', 'toggle-bookmark', 'toggle-blacklist'])

const { t } = useI18n()

const STATUS_COLOR = {
  pending: 'var(--portal-color-warning)',
  approved: 'var(--portal-color-success)',
  rejected: 'var(--portal-color-error)',
  blacklisted: 'var(--portal-color-neutral-dark)',
  watched: 'var(--portal-color-premium)',
  in_progress: 'var(--portal-color-info)',
}

const STATUS_LABEL_KEY = {
  pending: 'portal.posterCard.statusPending',
  approved: 'portal.posterCard.statusApproved',
  rejected: 'portal.posterCard.statusRejected',
  blacklisted: 'portal.posterCard.statusBlacklisted',
  watched: 'portal.posterCard.statusWatched',
  in_progress: 'portal.posterCard.statusInProgress',
}

const statusColor = computed(() => (props.status ? STATUS_COLOR[props.status] : null))
const statusLabel = computed(() =>
  props.status ? t(STATUS_LABEL_KEY[props.status]).toUpperCase() : '',
)

const action = computed(() => {
  if (props.availability === 'full') {
    return { label: t('portal.posterCard.actionPlay'), tone: 'play', icon: 'play' }
  }
  if (props.status === 'rejected') {
    return { label: t('portal.posterCard.actionReRequest'), tone: 'request', icon: 'rotate' }
  }
  if (props.status === 'pending' || props.status === 'approved') {
    return { label: t('portal.posterCard.actionPending'), tone: 'muted', icon: 'clock' }
  }
  return { label: t('portal.posterCard.actionRequest'), tone: 'request', icon: 'plus' }
})

function handlePrimaryAction() {
  if (action.value.tone === 'muted') return
  if (action.value.tone === 'play') emit('play')
  else emit('request')
}
</script>
