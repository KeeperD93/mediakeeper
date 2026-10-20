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
            availability === AVAILABILITY.FULL
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
            :href="embyHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src="/assets/icons/emby.svg" alt="" class="vmd2-btn-emby" />
            {{ $t('portal.hero.play') }}
          </a>

          <button
            v-if="showRequestBtn"
            class="vmd2-btn"
            :class="requestBtnClass"
            :disabled="!!requestBlockedReason"
            @click="$emit('request')"
          >
            <component :is="requestBtnIcon" />
            {{ requestBtnLabel }}
          </button>
          <p v-if="showRequestBtn && requestBlockedReason" class="dh-request-blocked">
            {{ requestBlockedReason }}
          </p>

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
import { AVAILABILITY, POSTER_STATUS_RIBBON } from '@/constants/portal'
import { REQUEST_STATUS } from '@/constants/requests'
import { Bookmark, Plus, RotateCcw, Video } from 'lucide-vue-next'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'
import { formatCountry, formatLanguage } from '@/utils/formatIntlLabel'
import { safeHref } from '@/utils/safeUrl'
import '@/assets/styles/portal/poster-card.css'

const props = defineProps({
  media: { type: Object, required: true },
  availInfo: { type: Object, default: null },
  reqStatus: { type: String, default: null },
  // Precomputed date hint surfaced as the native `title` tooltip on the
  // hero status ribbon. Empty string keeps the attribute off the DOM.
  reqStatusTooltip: { type: String, default: '' },
  // Computed by the page: the viewer may (re)request this title.
  showRequestBtn: { type: Boolean, default: false },
  // Non-empty when the viewer may NOT request this title (e.g. adult content
  // while the admin disallows adult requests): disables the button + shows why.
  requestBlockedReason: { type: String, default: '' },
  trailerKey: { type: String, default: null },
})

defineEmits(['request', 'open-trailer', 'add-to-list'])

const { t, locale } = useI18n()

// Gate the Emby deep-link through the scheme whitelist; falls back to a
// dead '#' if the stored URL ever carries an unsafe scheme.
const embyHref = computed(() => safeHref(props.availInfo?.emby_url) || '#')

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

// After a rejection the button reads "request again", like the poster cards.
const isRerequest = computed(() => props.reqStatus === REQUEST_STATUS.REJECTED)
const requestBtnLabel = computed(() =>
  t(isRerequest.value ? 'portal.detail.reRequest' : 'portal.detail.request'),
)
const requestBtnIcon = computed(() => (isRerequest.value ? RotateCcw : Plus))
const requestBtnClass = computed(() =>
  props.availInfo?.emby_url ? 'vmd2-btn--ghost' : 'vmd2-btn--secondary',
)

// The ribbon on the hero poster, with the poster cards' colours and labels:
// a request status or the blacklist marker ("available" shows none).
const statusRibbon = computed(() => {
  const look = props.reqStatus ? POSTER_STATUS_RIBBON[props.reqStatus] : null
  if (!look) return null
  return {
    label: t(look.labelKey).toUpperCase(),
    color: look.color,
    tooltip: props.reqStatusTooltip,
  }
})

// Availability chip for the hero poster — reuses the same markup +
// classes as PosterCard so styling stays consistent.
const availability = computed(() => {
  if (!props.availInfo?.emby_url) return null
  const a = props.availInfo.availability
  return a === AVAILABILITY.PARTIAL ? AVAILABILITY.PARTIAL : AVAILABILITY.FULL
})
</script>

<style scoped>
/* Greyed-out request button + its reason when the viewer can't request this
   title (adult content while admin requests are disabled). */
.vmd2-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.dh-request-blocked {
  margin-top: 0.4rem;
  max-width: 36ch;
  font-size: var(--portal-text-xs);
  line-height: 1.35;
  color: var(--portal-text-body-muted);
}
</style>
