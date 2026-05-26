<template>
  <div class="wlsc glass-card-wl">
    <!-- Card header -->
    <div class="wlsc-head" @click="((open = !open), !open && (expandedSeason = null))">
      <div class="wlsc-poster">
        <img
          v-if="posterUrl"
          :src="posterUrl"
          loading="lazy"
          @error="e => (e.target.style.display = 'none')"
        />
        <div v-else class="wlsc-poster-ph">📺</div>
      </div>
      <div class="wlsc-info">
        <div class="wlsc-name">
          {{ series.name }}
          <button class="wlsc-copy-btn" :title="$t('common.copy')" @click.stop="copyTitle">
            <Copy :size="14" />
          </button>
        </div>
        <div class="wlsc-meta">
          {{ series.total_seasons }} {{ $t('common.season', series.total_seasons) }} ·
          {{ series.year || '' }}
        </div>
      </div>
      <span class="wlsc-badge-red">{{ series._fm }}</span>
      <ChevronDown class="wlsc-chevron" :class="{ open }" :size="13" />
    </div>

    <!-- Barre de progression -->
    <div class="wlsc-progress">
      <div
        class="wlsc-progress-fill"
        :style="{ width: progress + '%', background: progressColor }"
      />
    </div>

    <!-- Seasons (LOCAL state to this card) -->
    <div v-if="open" class="wlsc-seasons">
      <div v-for="sn in series.seasons" :key="sn.season" class="wlsc-season">
        <div class="wlsc-season-head" @click.stop="toggleSeason(sn.season)">
          <span class="wlsc-season-check" :class="{ done: sn.all_present }">
            <Check v-if="sn.all_present" :size="9" :stroke-width="3" />
            <span v-else>·</span>
          </span>
          <span class="wlsc-season-num">S{{ pad(sn.season) }}</span>
          <span class="wlsc-season-ep">
            {{ sn.episode_count_emby }}/{{ sn.episode_count_tmdb }}
          </span>
          <span v-if="relevantEps(sn).length" class="wlsc-badge-sm">
            {{ relevantEps(sn).length }}
          </span>
          <div class="wlsc-season-actions" @click.stop>
            <button
              v-if="relevantEps(sn).length > 0"
              class="wlsc-ignore-season-btn"
              @click.stop="emitIgnoreSeason(sn)"
            >
              <Ban :size="10" />
              {{ $t('watchlist.ignoreSeason') }}
            </button>
          </div>
          <ChevronDown
            class="wlsc-chevron wlsc-chevron-sm"
            :class="{ open: expandedSeason === sn.season }"
            :size="11"
          />
        </div>

        <div v-if="expandedSeason === sn.season" class="wlsc-episodes">
          <div
            v-for="ep in sn.episodes"
            :key="ep.episode"
            class="wlsc-ep"
            :class="{
              present: ep.status === EPISODE_STATUS.PRESENT,
              ignored: isIgnored(sn.season, ep.episode),
            }"
          >
            <span class="wlsc-ep-dot" :style="{ background: epDotColor(ep, sn.season) }" />
            <span class="wlsc-ep-num">E{{ pad(ep.episode) }}</span>
            <span class="wlsc-ep-name">{{ ep.name || $t('watchlist.noTitle') }}</span>
            <span class="wlsc-ep-date">{{ formatDate(ep.air_date) }}</span>
            <span
              v-if="ep.status === EPISODE_STATUS.PRESENT && ep.audio_languages?.length"
              class="wlsc-ep-langs"
            >
              <span
                v-for="lang in ep.audio_languages"
                :key="lang"
                class="wlsc-ep-lang"
                :title="$t('watchlist.language_available')"
              >
                {{ lang }}
              </span>
            </span>
            <span v-if="ep.status === EPISODE_STATUS.PRESENT" class="wlsc-ep-check">✓</span>
            <span v-else-if="isIgnored(sn.season, ep.episode)" class="wlsc-ep-ignored">
              {{ $t('watchlist.ignoredLabel') }}
            </span>
            <button
              v-else-if="isRelevant(ep, sn.season)"
              class="wlsc-ep-ignore"
              @click.stop="$emit('ignore-ep', series.tmdb_id, sn.season, ep.episode)"
            >
              {{ $t('common.ignore') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Ban, Check, ChevronDown, Copy } from 'lucide-vue-next'
import { EPISODE_STATUS } from '@/constants/watchlist'

const props = defineProps({
  series: Object,
  ignoredSet: Object,
})
const emit = defineEmits(['ignore-ep', 'ignore-season'])

// ── LOCAL state to this card ──
const open = ref(false)
const expandedSeason = ref(null)

function toggleSeason(sn) {
  expandedSeason.value = expandedSeason.value === sn ? null : sn
}

const posterUrl = computed(() => props.series.emby_poster || props.series.poster || '')

const progress = computed(() => {
  const total = (props.series.seasons || []).reduce((a, sn) => a + sn.episode_count_tmdb, 0)
  const present = (props.series.seasons || []).reduce((a, sn) => a + sn.episode_count_emby, 0)
  return total ? Math.round((present / total) * 100) : 0
})
const progressColor = computed(() => {
  const p = progress.value
  if (p >= 80) return 'linear-gradient(90deg,var(--accent-500),var(--accent-400))'
  if (p >= 50) return 'linear-gradient(90deg,var(--color-warning),var(--color-warning))'
  return 'linear-gradient(90deg,var(--color-error),var(--color-error))'
})

function relevantEps(sn) {
  return sn.episodes.filter(
    e =>
      e.status === EPISODE_STATUS.MISSING &&
      !props.ignoredSet.has(`${props.series.tmdb_id}_s${sn.season}_e${e.episode}`),
  )
}
function isIgnored(season, ep) {
  return props.ignoredSet.has(`${props.series.tmdb_id}_s${season}_e${ep}`)
}
function isRelevant(ep, season) {
  return (
    ep.status === EPISODE_STATUS.MISSING &&
    !props.ignoredSet.has(`${props.series.tmdb_id}_s${season}_e${ep.episode}`)
  )
}
function epDotColor(ep, season) {
  if (ep.status === EPISODE_STATUS.PRESENT) return 'var(--color-success)'
  if (isIgnored(season, ep.episode)) return 'rgba(156,163,175,.3)'
  if (ep.status === EPISODE_STATUS.MISSING) return 'var(--color-error)'
  return 'var(--color-info)'
}
function pad(n) {
  return String(n).padStart(2, '0')
}
function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

function copyTitle() {
  navigator.clipboard.writeText(props.series.name).catch(() => {})
}

function emitIgnoreSeason(sn) {
  const keys = relevantEps(sn).map(e => `${props.series.tmdb_id}_s${sn.season}_e${e.episode}`)
  if (keys.length) emit('ignore-season', keys)
}
</script>

<style scoped>
.glass-card-wl {
  background: var(--surface-1);
  backdrop-filter: blur(10px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: border-color var(--duration-fast);
}
.glass-card-wl:hover {
  border-color: rgb(99, 102, 241, 0.2);
}
.wlsc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  cursor: pointer;
  user-select: none;
}
.wlsc-poster {
  width: 48px;
  height: 70px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
  flex-shrink: 0;
}
.wlsc-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wlsc-poster-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  opacity: 0.25;
}
.wlsc-info {
  flex: 1;
  min-width: 0;
}
.wlsc-name {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 4px;
}
.wlsc-copy-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--duration-fast);
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;
}
.wlsc-copy-btn:hover {
  color: var(--accent-400);
}
.wlsc-head:hover .wlsc-copy-btn {
  opacity: 0.7;
}
.wlsc-meta {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 3px;
}
.wlsc-badge-red {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: rgb(var(--color-error-rgb), 0.12);
  color: var(--color-error);
  flex-shrink: 0;
}
.wlsc-chevron {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform var(--duration-base);
}
.wlsc-chevron.open {
  transform: rotate(180deg);
}
.wlsc-chevron-sm {
  margin-left: 4px;
}
.wlsc-progress {
  height: 2px;
  background: var(--surface-2);
  margin: 0 12px 10px;
  border-radius: 2px;
  overflow: hidden;
}
.wlsc-progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}
.wlsc-seasons {
  padding: 0 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.wlsc-season {
  background: rgb(0, 0, 0, 0.2);
  border: 0.5px solid rgb(255, 255, 255, 0.05);
  border-radius: var(--radius-btn);
  overflow: hidden;
}
.wlsc-season-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}
.wlsc-season-head:hover {
  background: var(--surface-1);
}
.wlsc-season-check {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-3xs);
  background: rgb(107, 114, 128, 0.15);
  color: #6b7280;
  flex-shrink: 0;
}
.wlsc-season-check.done {
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
}
.wlsc-season-num {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.wlsc-season-ep {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  font-family: 'SF Mono', monospace;
}
.wlsc-badge-sm {
  font-size: 0.58rem;
  font-weight: var(--font-bold);
  padding: 2px 7px;
  border-radius: 5px;
  background: rgb(var(--color-error-rgb), 0.12);
  color: var(--color-error);
}
.wlsc-season-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.wlsc-ignore-season-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-3xs);
  padding: 2px 7px;
  border-radius: 5px;
  border: none;
  cursor: pointer;
  background: rgb(156, 163, 175, 0.1);
  color: rgb(156, 163, 175, 0.6);
  font-family: inherit;
  transition: all var(--duration-fast);
}
.wlsc-ignore-season-btn:hover {
  background: rgb(var(--color-error-rgb), 0.15);
  color: var(--color-error);
}
.wlsc-episodes {
  padding: 3px 8px 8px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.wlsc-ep {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background 0.1s;
}
.wlsc-ep:hover {
  background: var(--surface-1);
}
.wlsc-ep.present {
  opacity: 0.3;
}
.wlsc-ep.ignored {
  opacity: 0.4;
}
.wlsc-ep-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.wlsc-ep-num {
  font-size: var(--text-2xs);
  font-family: 'SF Mono', monospace;
  font-weight: var(--font-bold);
  color: var(--accent-400);
  width: 32px;
  flex-shrink: 0;
}
.wlsc-ep-name {
  font-size: var(--text-xs);
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wlsc-ep-date {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  flex-shrink: 0;
  font-family: 'SF Mono', monospace;
}
.wlsc-ep-check {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.58rem;
  flex-shrink: 0;
}
.wlsc-ep-langs {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}
.wlsc-ep-lang {
  font-size: 0.58rem;
  font-weight: var(--font-bold);
  letter-spacing: 0.3px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-secondary);
  font-family: 'SF Mono', monospace;
  cursor: help;
}
.wlsc-ep-ignored {
  font-size: 0.58rem;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgb(107, 114, 128, 0.1);
  color: rgb(107, 114, 128, 0.5);
  flex-shrink: 0;
}
.wlsc-ep-ignore {
  font-size: var(--text-3xs);
  padding: 2px 7px;
  border-radius: 5px;
  background: rgb(107, 114, 128, 0.1);
  color: #9ca3af;
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast);
  font-family: inherit;
  flex-shrink: 0;
}
.wlsc-ep-ignore:hover {
  background: rgb(var(--color-error-rgb), 0.15);
  color: var(--color-error);
}
</style>
