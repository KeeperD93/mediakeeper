<template>
  <section class="vmd2-hero">
    <div
      class="vmd2-hero-bg"
      :style="media.backdrop ? { backgroundImage: `url(${media.backdrop})` } : null"
    />

    <div class="vmd2-hero-content">
      <div v-if="media.poster" class="vmd2-poster-wrap">
        <img class="vmd2-poster" :src="media.poster" :alt="media.title" />
        <PremiumRibbon
          v-if="statusRibbon"
          :label="statusRibbon.label"
          :bg="statusRibbon.color"
          :title="statusRibbon.tooltip"
        />
        <div
          v-if="availability"
          class="mk-poster__avail"
          :class="`mk-poster__avail--${availability}`"
        >
          <span class="mk-poster__avail-dot" />
          {{
            availability === 'full'
              ? $t('portal.posterCard.availFull')
              : $t('portal.posterCard.availPartial')
          }}
        </div>
      </div>

      <div class="vmd2-hero-info">
        <div v-if="topStudios.length" class="vmd2-studios">
          <img
            v-for="s in topStudios"
            :key="s.name"
            :src="s.logo"
            :alt="s.name"
            class="vmd2-studio-logo"
          />
        </div>

        <h1 class="vmd2-title">{{ media.title }}</h1>
        <p v-if="media.tagline" class="vmd2-tagline">« {{ media.tagline }} »</p>

        <div class="vmd2-facts">
          <span v-if="media.year">{{ media.year }}</span>
          <span v-if="runtimeLabel">• {{ runtimeLabel }}</span>
          <span v-if="media.certification" class="vmd2-cert">{{ media.certification }}</span>
          <span v-if="languageLabel">• {{ languageLabel }}</span>
          <span v-if="countryLabel">• {{ countryLabel }}</span>
        </div>

        <div v-if="tmdbPct" class="vmd2-scores">
          <div class="vmd2-score vmd2-score--tmdb">
            <span class="vmd2-score-dot" />
            <div>
              <div class="vmd2-score-value">{{ tmdbPct }}%</div>
              <div class="vmd2-score-label">TMDB</div>
            </div>
          </div>
          <div v-if="media.vote_count" class="vmd2-score">
            <span class="vmd2-score-dot vmd2-score-dot--muted" />
            <div>
              <div class="vmd2-score-value">{{ media.vote_count.toLocaleString() }}</div>
              <div class="vmd2-score-label">{{ $t('portal.detail.votes') }}</div>
            </div>
          </div>
          <div v-if="media.popularity" class="vmd2-score vmd2-score--audience">
            <span class="vmd2-score-dot" />
            <div>
              <div class="vmd2-score-value">{{ Math.round(media.popularity) }}</div>
              <div class="vmd2-score-label">{{ $t('portal.detail.popularity') }}</div>
            </div>
          </div>
        </div>

        <div v-if="media.genres?.length" class="vmd2-genres">
          <span v-for="g in media.genres" :key="g" class="vmd2-genre">{{ g }}</span>
        </div>

        <div class="vmd2-actions">
          <a
            v-if="availInfo?.emby_url"
            class="vmd2-btn vmd2-btn--primary"
            :href="availInfo.emby_url"
            target="_blank"
          >
            <img src="/assets/icons/emby.svg" alt="" class="vmd2-btn-emby" />
            {{ $t('portal.hero.play') }}
          </a>

          <button
            v-if="showRequestBtn && !reqStatus"
            class="vmd2-btn"
            :class="requestBtnClass"
            @click="$emit('request')"
          >
            <component :is="requestBtnIcon" />
            {{ requestBtnLabel }}
          </button>

          <button v-if="trailerKey" class="vmd2-btn vmd2-btn--ghost" @click="$emit('open-trailer')">
            <Video :size="16" />
            {{ $t('portal.detail.watchTrailer') }}
          </button>

          <button
            class="vmd2-btn vmd2-btn--ghost vmd2-btn--icon"
            :title="$t('portal.detail.addToList')"
            @click="$emit('add-to-list')"
          >
            <Bookmark :size="18" />
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { REQUEST_STATUS } from '@/constants/requests'
import { Bookmark, Plus, Video } from 'lucide-vue-next'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'
import { formatCountry, formatLanguage } from '@/utils/formatIntlLabel'
import '@/assets/styles/portal/poster-card.css'

const props = defineProps({
  media: { type: Object, required: true },
  availInfo: { type: Object, default: null },
  reqStatus: { type: String, default: null },
  // Precomputed date hint surfaced as the native `title` tooltip on the
  // hero status ribbon. Empty string keeps the attribute off the DOM.
  reqStatusTooltip: { type: String, default: '' },
  showRequestBtn: { type: Boolean, default: false },
  trailerKey: { type: String, default: null },
})

defineEmits(['request', 'open-trailer', 'add-to-list'])

const { t, locale } = useI18n()

const topStudios = computed(() => (props.media.studios || []).filter(s => s.logo).slice(0, 3))

const tmdbPct = computed(() => {
  const v = props.media.vote
  return v ? Math.round(v * 10) : 0
})

const runtimeLabel = computed(() => {
  const r = props.media.runtime
  if (!r) return ''
  const h = Math.floor(r / 60)
  const m = r % 60
  return h > 0 ? `${h}h${m > 0 ? m : ''}` : `${m}min`
})

const languageLabel = computed(() => formatLanguage(props.media.original_language, locale.value))
const countryLabel = computed(() => formatCountry(props.media.country_codes?.[0], locale.value))

const requestBtnLabel = computed(() => t('portal.detail.request'))
const requestBtnIcon = computed(() => Plus)
const requestBtnClass = computed(() =>
  props.availInfo?.emby_url ? 'vmd2-btn--ghost' : 'vmd2-btn--secondary',
)

// Single status descriptor that drives the PremiumRibbon on the hero
// poster. Reuses the same colour tokens and i18n keys as PosterCard so
// the detail page and the grid speak the same visual language.
const STATUS_COLOR = {
  pending: 'var(--portal-color-warning)',
  approved: 'var(--portal-color-success)',
  rejected: 'var(--portal-color-error)',
  blacklisted: 'var(--portal-color-neutral-dark)',
}
const STATUS_LABEL_KEY = {
  pending: 'portal.posterCard.statusPending',
  approved: 'portal.posterCard.statusApproved',
  rejected: 'portal.posterCard.statusRejected',
  blacklisted: 'portal.posterCard.statusBlacklisted',
}
const statusRibbon = computed(() => {
  const s = props.reqStatus
  if (!s) return null
  if (s === REQUEST_STATUS.PENDING)
    return {
      label: t(STATUS_LABEL_KEY.pending).toUpperCase(),
      color: STATUS_COLOR.pending,
      tooltip: props.reqStatusTooltip,
    }
  if (s === REQUEST_STATUS.APPROVED)
    return {
      label: t(STATUS_LABEL_KEY.approved).toUpperCase(),
      color: STATUS_COLOR.approved,
      tooltip: props.reqStatusTooltip,
    }
  if (s === REQUEST_STATUS.REJECTED)
    return {
      label: t(STATUS_LABEL_KEY.rejected).toUpperCase(),
      color: STATUS_COLOR.rejected,
      tooltip: props.reqStatusTooltip,
    }
  if (s === 'blacklisted')
    return {
      label: t(STATUS_LABEL_KEY.blacklisted).toUpperCase(),
      color: STATUS_COLOR.blacklisted,
      tooltip: props.reqStatusTooltip,
    }
  return null
})

// Availability chip for the hero poster — reuses the same markup +
// classes as PosterCard so styling stays consistent.
const availability = computed(() => {
  if (!props.availInfo?.emby_url) return null
  const a = props.availInfo.availability
  return a === 'partial' ? 'partial' : 'full'
})
</script>
