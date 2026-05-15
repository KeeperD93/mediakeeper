<template>
  <section class="vmd2-hero">
    <div
      class="vmd2-hero-bg"
      :style="media.backdrop ? { backgroundImage: `url(${media.backdrop})` } : null"
    />

    <div class="vmd2-hero-content">
      <div v-if="media.poster" class="vmd2-poster-wrap">
        <img class="vmd2-poster" :src="media.poster" :alt="media.title" />
        <span
          v-if="statusTag"
          class="vmd2-poster-status"
          :class="`vmd2-poster-status--${statusTag.variant}`"
        >
          {{ statusTag.label }}
        </span>
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

        <div v-if="availInfo?.emby_url" class="vmd2-availability">
          <span class="vmd2-avail-note">{{ $t('portal.detail.availableOnEmby') }}</span>
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

const props = defineProps({
  media: { type: Object, required: true },
  availInfo: { type: Object, default: null },
  reqStatus: { type: String, default: null },
  showRequestBtn: { type: Boolean, default: false },
  trailerKey: { type: String, default: null },
})

defineEmits(['request', 'open-trailer', 'add-to-list'])

const { t } = useI18n()

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

const languageLabel = computed(
  () => props.media.languages?.[0] || props.media.original_language?.toUpperCase() || '',
)
const countryLabel = computed(() => props.media.countries?.[0] || '')

const requestBtnLabel = computed(() => t('portal.detail.request'))
const requestBtnIcon = computed(() => Plus)
const requestBtnClass = computed(() =>
  props.availInfo?.emby_url ? 'vmd2-btn--ghost' : 'vmd2-btn--secondary',
)

// Status tag stacked under the certification badge on the poster. Replaces
// the disabled "Approved / Rejected / Requested / Available" buttons so the
// action bar stays clean and the state reads as a visual badge.
const statusTag = computed(() => {
  const s = props.reqStatus
  if (!s) return null
  if (s === REQUEST_STATUS.REJECTED)
    return { variant: 'rejected', label: t('portal.detail.rejectedBtn') }
  if (s === REQUEST_STATUS.APPROVED)
    return { variant: 'approved', label: t('portal.detail.approvedBtn') }
  if (s === 'available') return { variant: 'available', label: t('portal.detail.availableBtn') }
  return { variant: 'requested', label: t('portal.card.requestedBtn') }
})
</script>
