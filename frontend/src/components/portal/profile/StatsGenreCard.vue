<template>
  <div class="gc-genre-cards-box">
    <h4 class="gc-box-title">{{ $t('portal.profile.yourGenres') }}</h4>

    <!-- Row 1: genre cards (horizontal scroller) -->
    <div class="gc-genre-scroll">
      <div
        v-for="g in (stats.top_genres || []).slice(0, 6)"
        :key="g.id"
        class="gc-genre-card"
        :style="{ '--gc': genreColor[g.id] || '#818cf8' }"
      >
        <div class="gc-genre-emoji">
          <component :is="iconFor(g.id)" :size="22" />
        </div>
        <div class="gc-genre-cname">{{ genreName(g.id) }}</div>
        <div class="gc-genre-cbar">
          <div class="gc-genre-cfill" :style="{ width: g.percentage + '%' }" />
        </div>
        <div class="gc-genre-cpct">{{ g.percentage }}%</div>
        <div v-if="g.count" class="gc-genre-ccount">
          {{ g.count }} {{ $t('portal.profile.viewedCount') }}
        </div>
      </div>
    </div>

    <!-- Row 2: behavioural tiles (3 equal columns) -->
    <div class="gc-tile-row gc-tile-row--trio">
      <!-- Favourite day -->
      <div class="gc-tile gc-tile--day">
        <div class="gc-tile-header">
          <CalendarDays :size="14" class="gc-tile-icon" />
          <span class="gc-tile-label">{{ $t('portal.profile.favoriteDay') }}</span>
        </div>
        <div class="gc-daychart">
          <div v-for="day in weekData" :key="day.label" class="gc-daybar-wrap">
            <div class="gc-daybar">
              <div
                class="gc-daybar-fill"
                :style="{ height: day.pct + '%' }"
                :class="{ 'gc-daybar-fill--top': day.top }"
              />
            </div>
            <span class="gc-daylabel" :class="{ 'gc-daylabel--top': day.top }">
              {{ day.label }}
            </span>
          </div>
        </div>
        <div class="gc-tile-footer">
          <strong>{{ topDay }}</strong>
        </div>
      </div>

      <!-- Longest marathon -->
      <div class="gc-tile gc-tile--marathon">
        <div class="gc-tile-header">
          <Flame :size="14" class="gc-tile-icon gc-tile-icon--fire" />
          <span class="gc-tile-label">{{ $t('portal.profile.longestMarathon') }}</span>
        </div>
        <div class="gc-marathon-big">{{ marathonLabel }}</div>
        <div class="gc-tile-footer">{{ $t('portal.profile.longestMarathonSub') }}</div>
      </div>

      <!-- Movies vs series ratio -->
      <div class="gc-tile gc-tile--ratio">
        <div class="gc-tile-header">
          <Film :size="14" class="gc-tile-icon gc-tile-icon--film" />
          <span class="gc-tile-label">{{ $t('portal.profile.mediaRatio') }}</span>
        </div>
        <div v-if="hasMediaRatio" class="gc-ratio">
          <div class="gc-ratio-donut" :style="donutStyle" aria-hidden="true">
            <span class="gc-ratio-donut-inner">
              {{ moviePct }}
              <small>%</small>
            </span>
          </div>
          <div class="gc-ratio-legend">
            <div class="gc-ratio-line">
              <span class="gc-ratio-dot gc-ratio-dot--movie" />
              <span class="gc-ratio-pct">{{ moviePct }}%</span>
              <span class="gc-ratio-label">{{ $t('portal.profile.mediaRatioMovies') }}</span>
              <span class="gc-ratio-count">{{ stats.media_ratio.movie_plays }}</span>
            </div>
            <div class="gc-ratio-line">
              <span class="gc-ratio-dot gc-ratio-dot--series" />
              <span class="gc-ratio-pct">{{ seriesPct }}%</span>
              <span class="gc-ratio-label">{{ $t('portal.profile.mediaRatioSeries') }}</span>
              <span class="gc-ratio-count">{{ stats.media_ratio.series_plays }}</span>
            </div>
          </div>
        </div>
        <div v-else class="gc-tile-empty">—</div>
      </div>
    </div>

    <!-- Row 3: time-of-day + record month -->
    <div class="gc-tile-row gc-tile-row--duo">
      <div class="gc-tile gc-tile--hours">
        <div class="gc-tile-header">
          <Clock :size="14" class="gc-tile-icon gc-tile-icon--clock" />
          <span class="gc-tile-label">{{ $t('portal.profile.timeOfDay') }}</span>
        </div>
        <div class="gc-hours">
          <div
            v-for="b in hourBuckets"
            :key="b.bucket"
            class="gc-hourcol"
            :class="{ 'gc-hourcol--top': b.top }"
          >
            <div class="gc-hourbar">
              <div class="gc-hourbar-fill" :style="{ height: b.pct + '%' }" />
            </div>
            <div class="gc-hourlbl">{{ b.label }}</div>
            <div class="gc-hourval">{{ b.count }}</div>
          </div>
        </div>
        <div class="gc-tile-footer">
          <strong>{{ topHourLabel }}</strong>
        </div>
      </div>

      <div class="gc-tile gc-tile--record">
        <div class="gc-tile-header">
          <Trophy :size="14" class="gc-tile-icon gc-tile-icon--trophy" />
          <span class="gc-tile-label">{{ $t('portal.profile.recordMonth') }}</span>
        </div>
        <div v-if="stats.record_month?.count" class="gc-record">
          <div class="gc-record-month">{{ recordMonthLabel }}</div>
          <div class="gc-record-count">
            <strong>{{ stats.record_month.count }}</strong>
            <span>{{ $t('portal.profile.playsSuffix') }}</span>
          </div>
        </div>
        <div v-else class="gc-tile-empty">—</div>
      </div>
    </div>

    <!-- Row 4: most rewatched (2 equal columns, with bigger posters) -->
    <div class="gc-tile-row gc-tile-row--duo">
      <div class="gc-tile gc-tile--rewatch">
        <div class="gc-tile-header">
          <Clapperboard :size="14" class="gc-tile-icon" />
          <span class="gc-tile-label">{{ $t('portal.profile.mostRewatchedMovie') }}</span>
        </div>
        <div v-if="stats.most_rewatched_movie" class="gc-rewatch">
          <div class="gc-rewatch-poster">
            <img
              v-if="stats.most_rewatched_movie.poster_url"
              :src="stats.most_rewatched_movie.poster_url"
              class="gc-rewatch-poster-img"
            />
            <div v-else class="gc-rewatch-placeholder">🎬</div>
          </div>
          <div class="gc-rewatch-info">
            <div class="gc-rewatch-title">{{ stats.most_rewatched_movie.title }}</div>
            <div class="gc-rewatch-count">
              {{ $t('portal.profile.viewedPrefix') }}
              <strong>
                {{ stats.most_rewatched_movie.count }} {{ $t('portal.profile.timesSuffix') }}
              </strong>
            </div>
          </div>
        </div>
        <div v-else class="gc-tile-empty">—</div>
      </div>

      <div class="gc-tile gc-tile--rewatch">
        <div class="gc-tile-header">
          <Tv :size="14" class="gc-tile-icon" />
          <span class="gc-tile-label">{{ $t('portal.profile.mostRewatchedSeries') }}</span>
        </div>
        <div v-if="stats.most_rewatched_series" class="gc-rewatch">
          <div class="gc-rewatch-poster">
            <img
              v-if="stats.most_rewatched_series.poster_url"
              :src="stats.most_rewatched_series.poster_url"
              class="gc-rewatch-poster-img"
            />
            <div v-else class="gc-rewatch-placeholder">📺</div>
          </div>
          <div class="gc-rewatch-info">
            <div class="gc-rewatch-title">{{ stats.most_rewatched_series.title }}</div>
            <div class="gc-rewatch-count">
              <strong>
                {{ stats.most_rewatched_series.count }} {{ $t('portal.profile.episodesSuffix') }}
              </strong>
              {{ $t('portal.profile.rewatchedSuffix') }}
            </div>
          </div>
        </div>
        <div v-else class="gc-tile-empty">—</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  CalendarDays,
  Flame,
  Film,
  Clapperboard,
  Tv,
  Clock,
  Trophy,
  Zap,
  Laugh,
  Drama,
  AlertTriangle,
  Compass,
  Ghost,
  Rocket,
  Palette,
  Sparkles,
  Users,
  Camera,
  Search,
  Shield,
  Heart,
  Clapperboard as ClapperboardFallback,
} from 'lucide-vue-next'

const { t } = useI18n()

const props = defineProps({
  stats: { type: Object, required: true },
  weekData: { type: Array, required: true },
  topDay: { type: String, default: '—' },
  genreName: { type: Function, required: true },
  genreColor: { type: Object, required: true },
  genreEmoji: { type: Object, required: true },
  genreIcon: { type: Object, default: () => ({}) },
})

const GENRE_ICON_REGISTRY = {
  Zap,
  Laugh,
  Drama,
  AlertTriangle,
  Compass,
  Ghost,
  Rocket,
  Palette,
  Sparkles,
  Users,
  Camera,
  Search,
  Shield,
  Heart,
}
function iconFor(genreId) {
  const name = props.genreIcon[genreId]
  return GENRE_ICON_REGISTRY[name] || ClapperboardFallback
}

const marathonLabel = computed(() => {
  const mins = props.stats.longest_session_minutes || 0
  if (mins <= 0) return '—'
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? t('portal.profile.hmFormat', { h, m }) : `${m} min`
})

const mediaTotals = computed(() => {
  const mr = props.stats.media_ratio || {}
  const movies = mr.movie_minutes || 0
  const series = mr.series_minutes || 0
  return { movies, series, total: movies + series }
})
const hasMediaRatio = computed(() => mediaTotals.value.total > 0)
const moviePct = computed(() => {
  const { movies, total } = mediaTotals.value
  return total > 0 ? Math.round((100 * movies) / total) : 0
})
const seriesPct = computed(() => (hasMediaRatio.value ? 100 - moviePct.value : 0))
const donutStyle = computed(() => ({
  background: `conic-gradient(#a855f7 0 ${moviePct.value}%, #38bdf8 ${moviePct.value}% 100%)`,
}))

const HOUR_LABELS = {
  morning: () => t('portal.profile.hourMorning'),
  afternoon: () => t('portal.profile.hourAfternoon'),
  evening: () => t('portal.profile.hourEvening'),
  night: () => t('portal.profile.hourNight'),
}
const hourBuckets = computed(() => {
  const src = props.stats.hour_buckets || []
  const max = Math.max(1, ...src.map(b => b.count || 0))
  const top = src.reduce((acc, b) => (b.count > (acc?.count || 0) ? b : acc), null)
  return src.map(b => ({
    bucket: b.bucket,
    count: b.count || 0,
    label: HOUR_LABELS[b.bucket]?.() || b.bucket,
    pct: max > 0 ? Math.round((100 * b.count) / max) : 0,
    top: top && b.bucket === top.bucket && b.count > 0,
  }))
})
const topHourLabel = computed(() => {
  const top = hourBuckets.value.find(b => b.top)
  return top ? top.label : '—'
})

const recordMonthLabel = computed(() => {
  const m = props.stats.record_month?.month
  if (!m) return '—'
  const [year, month] = m.split('-')
  const date = new Date(Number(year), Number(month) - 1, 1)
  return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
})
</script>

<style>
@import url('@/assets/styles/portal/stats-card.css');
</style>
