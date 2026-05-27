<template>
  <Teleport to="body">
    <transition name="np-fade">
      <div
        v-if="visible"
        ref="panelRef"
        class="np-overlay"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        tabindex="-1"
        @click.self="emit('close')"
      >
        <!-- Backdrop -->
        <div class="np-backdrop">
          <img
            v-if="session.thumb_url"
            :src="session.thumb_url"
            @error="$event => ($event.target.style.display = 'none')"
          />
        </div>
        <div class="np-gradient" />

        <!-- Close -->
        <MkButton
          variant="icon"
          icon="x"
          size="sm"
          :aria-label="$t('common.close')"
          class="np-close-wrap"
          @click="emit('close')"
        />

        <!-- Content -->
        <div class="np-content">
          <div v-if="session.thumb_url" class="np-poster">
            <img
              :src="session.thumb_url"
              @error="$event => ($event.target.style.display = 'none')"
            />
          </div>

          <div class="np-info">
            <div class="np-badge">
              <span
                class="np-status-dot"
                :class="session.is_playing ? 'np-dot-green' : 'np-dot-yellow'"
              />
              <span class="np-badge-label">
                {{ session.is_playing ? $t('dashboard.playing') : $t('dashboard.paused') }}
              </span>
            </div>

            <h1 :id="titleId" class="np-title">{{ session.series || session.media }}</h1>
            <p class="np-sub">
              {{
                session.episode
                  ? `${session.episode} · ${session.media}`
                  : session.media_type || $t('common.film')
              }}
            </p>

            <div class="np-user-row">
              <span class="np-user-label">{{ session.user }}</span>
              <span class="np-device">{{ session.client || session.device || '' }}</span>
            </div>

            <!-- Progress bar -->
            <div class="np-progress-wrap">
              <div class="np-progress-bg">
                <div class="np-progress-fill" :style="{ width: (session.progress || 0) + '%' }" />
              </div>
              <span class="np-progress-pct">{{ Math.round(session.progress || 0) }}%</span>
            </div>

            <!-- TMDB info if available -->
            <div v-if="tmdbData" class="np-tmdb">
              <div class="np-tmdb-chips">
                <span v-if="tmdbData.year" class="np-chip">{{ tmdbData.year }}</span>
                <span v-if="tmdbData.vote" class="np-chip np-chip-vote">
                  ⭐ {{ tmdbData.vote }}
                </span>
                <span v-if="tmdbData.runtime" class="np-chip">
                  {{ $t('dashboard.runtimeMinutes', { n: tmdbData.runtime }) }}
                </span>
                <span v-if="tmdbData.seasons_count" class="np-chip">
                  {{
                    $t(
                      'dashboard.seasonsCount',
                      { n: tmdbData.seasons_count },
                      tmdbData.seasons_count,
                    )
                  }}
                </span>
              </div>
              <div v-if="tmdbData.genres?.length" class="np-genres">
                <span v-for="g in tmdbData.genres" :key="g" class="np-genre">{{ g }}</span>
              </div>
              <p v-if="tmdbData.overview" class="np-overview">{{ tmdbData.overview }}</p>
            </div>
            <div v-else-if="tmdbLoading" class="np-tmdb-loading">
              {{ $t('dashboard.loadingTmdb') }}
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, toRef, useId, watch } from 'vue'
import MkButton from '@/components/common/MkButton.vue'
import { useApi } from '@/composables/useApi'
import { useFocusTrap } from '@/composables/useFocusTrap'

const props = defineProps({
  visible: { type: Boolean, default: false },
  session: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close'])

const { apiGet } = useApi()
const tmdbData = ref(null)
const tmdbLoading = ref(false)
const cache = {}

// Modal a11y wiring: aria-labelledby points at the dialog title,
// focus trap activates on `visible`, Escape calls close, previously
// focused element is restored on deactivate.
const titleId = useId()
const panelRef = ref(null)
useFocusTrap({
  active: toRef(props, 'visible'),
  containerRef: panelRef,
  onEscape: () => emit('close'),
})

watch(
  () => props.visible,
  async v => {
    if (!v) return
    const name = props.session.series || props.session.media || ''
    if (!name) return

    // Extract base series/movie name
    const base = name
      .replace(/ - S\d+.*$/i, '')
      .replace(/ S\d+E\d+.*$/i, '')
      .trim()
    if (cache[base]) {
      tmdbData.value = cache[base]
      return
    }

    tmdbLoading.value = true
    tmdbData.value = null
    try {
      const results = await apiGet(`/api/watchlist/search?q=${encodeURIComponent(base)}`)
      if (results?.length > 0) {
        const best = results[0]
        const detail = await apiGet(`/api/watchlist/tmdb/${best.media_type}/${best.tmdb_id}`)
        if (detail && !detail.error) {
          cache[base] = detail
          tmdbData.value = detail
        }
      }
    } catch {
      /* silent: TMDB enrichment, overlay keeps plain data */
    }
    tmdbLoading.value = false
  },
)
</script>

<style scoped>
.np-fade-enter-active,
.np-fade-leave-active {
  transition: opacity var(--duration-slow) ease;
}
.np-fade-enter-from,
.np-fade-leave-to {
  opacity: 0;
}

.np-overlay {
  position: fixed;
  inset: 0;
  /* Sits between --z-overlay (9000) and --z-toast (9999) — pure
     literal so the fullscreen card is above the dashboard backdrop
     but yields to global toasts. */
  z-index: 9500;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.np-backdrop {
  position: absolute;
  inset: 0;
}
.np-backdrop img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: blur(20px) brightness(0.3) saturate(1.3);
  transform: scale(1.1);
}
.np-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgb(0, 0, 0, 0.7) 0%,
    rgb(0, 0, 0, 0.3) 50%,
    rgb(0, 0, 0, 0.7) 100%
  );
}

.np-close-wrap {
  position: absolute;
  top: var(--space-6);
  /* 28 px right inset — between --space-6 (24) and --space-8 (32). */
  right: 28px;
  z-index: 10;
}

.np-content {
  position: relative;
  z-index: 2;
  display: flex;
  /* Mobile-first defaults — stacked column, centered, compact paddings.
     Desktop layout (side-by-side, larger paddings) lives in the
     @media (min-width: 768px) block below. */
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-6);
  max-width: 900px;
  padding: var(--space-6);
}

.np-poster {
  /* Mobile-first poster size — 160 / 240 px, 2:3 ratio. Desktop bumps
     to 220 / 330 px via the @media (min-width: 768px) block below. */
  width: 160px;
  height: 240px;
  border-radius: var(--radius-card);
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: var(--shadow-lg);
  border: var(--border-width) solid var(--border-intense);
  animation: np-poster-in var(--duration-slower) ease-out 0.1s both;
}
@keyframes np-poster-in {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.np-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.np-info {
  flex: 1;
  min-width: 0;
  animation: np-info-in var(--duration-slower) ease-out 0.2s both;
}
@keyframes np-info-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.np-badge {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.np-status-dot {
  /* 10 px badge dot — too small for any --icon-* token. */
  width: 10px;
  height: 10px;
  border-radius: var(--radius-circle);
  animation: np-status-pulse var(--duration-pulse) ease-in-out infinite;
}
.np-dot-green {
  background: var(--color-online);
  box-shadow: 0 0 8px rgb(var(--color-online-rgb), 0.5);
}
.np-dot-yellow {
  background: var(--color-warning);
  box-shadow: 0 0 8px rgb(var(--color-warning-rgb), 0.5);
}
@keyframes np-status-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.np-badge-label {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  /* 1.5 px tracking — above --tracking-widest's 0.06em (~0.84 px at
     14 px font). Fullscreen-only emphasis. */
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.np-title {
  /* Mobile-first title — 24 px between --text-lg (~20.8) and --text-xl.
     Desktop bumps to 36 px (well above --text-xl's clamp max,
     fullscreen-only signature) via the @media (min-width: 768px) block. */
  font-size: 24px;
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0 0 6px;
  line-height: var(--lh-snug-tight);
}
.np-sub {
  font-size: var(--text-md);
  color: var(--text-faint);
  margin: 0 0 var(--space-4);
}

.np-user-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.np-user-label {
  font-size: var(--text-base);
  color: var(--text-secondary);
  font-weight: var(--font-regular);
}
.np-device {
  font-size: var(--text-xs);
  color: var(--text-very-faint);
}

.np-progress-wrap {
  display: flex;
  align-items: center;
  /* Mobile-first centers the progress bar; desktop left-aligns via the
     @media (min-width: 768px) block. */
  justify-content: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}
.np-progress-bg {
  flex: 1;
  /* 5 px bar — fullscreen-specific, between --border-width and
     a 6 px scale step. */
  height: 5px;
  background: var(--surface-3);
  border-radius: 3px;
  /* 350 px cap — fullscreen-specific. */
  max-width: 350px;
}
.np-progress-fill {
  height: 5px;
  background: linear-gradient(90deg, var(--accent-500), var(--accent-300));
  border-radius: 3px;
  transition: width var(--duration-slower);
}
.np-progress-pct {
  font-size: var(--text-sm);
  color: var(--text-faint);
  font-variant-numeric: tabular-nums;
}

/* TMDB info */
.np-tmdb {
  /* 0.4 s duration + 0.4 s delay — staggered cascade after .np-info
     (0.5 s + 0.2 s). Hors palier --duration-* (slow 0.3 / slower 0.5)
     pour préserver le timing d'apparition de la fiche TMDB enrichie. */
  animation: np-info-in 0.4s ease-out 0.4s both;
}
.np-tmdb-chips {
  display: flex;
  flex-wrap: wrap;
  /* 6 px chip gap — between --space-1 and --space-2. */
  gap: 6px;
  margin-bottom: var(--space-2-5);
}
.np-chip {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  color: var(--text-faint);
}
.np-chip-vote {
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
}
.np-genres {
  display: flex;
  flex-wrap: wrap;
  /* 5 px genre gap — between --space-1 (4) and --space-2 (8). */
  gap: 5px;
  margin-bottom: var(--space-3-5);
}
.np-genre {
  font-size: var(--text-2xs);
  /* 3 / 10 px chip padding — vertical between --space-half and
     --space-1, horizontal --space-2-5. */
  padding: 3px var(--space-2-5);
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  color: var(--text-faint);
}
.np-overview {
  font-size: var(--text-base);
  color: var(--text-faint);
  line-height: var(--lh-relaxed);
  margin: 0;
  /* 120 px cap on the synopsis — fullscreen-only safeguard. */
  max-height: 120px;
  overflow-y: auto;
}
.np-tmdb-loading {
  font-size: var(--text-xs);
  color: var(--text-very-faint);
}

.np-overview::-webkit-scrollbar {
  /* 3 px scrollbar — narrower than --scrollbar-width (6). */
  width: 3px;
}
.np-overview::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 2px;
}

@media (min-width: 768px) {
  .np-content {
    flex-direction: row;
    align-items: flex-start;
    text-align: left;
    /* 40 px gap between poster and info — between --space-8 (32) and a
       hypothetical space-10. Fullscreen-only, kept literal. */
    gap: 40px;
    /* 48 px overlay padding — between --space-6 (24) and --space-8 (32)
       times two. Fullscreen-only literal. */
    padding: 48px;
  }
  .np-poster {
    /* 220 / 330 px poster signature on tablets and desktop. */
    width: 220px;
    height: 330px;
  }
  .np-title {
    /* 36 px fullscreen hero title — well above --text-xl's clamp max. */
    font-size: 36px;
  }
  .np-progress-wrap {
    justify-content: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .np-fade-enter-active,
  .np-fade-leave-active {
    transition: none;
  }
  .np-poster,
  .np-info,
  .np-tmdb {
    animation: none;
    opacity: 1;
    transform: none;
  }
  .np-status-dot {
    animation: none;
  }
  .np-progress-fill {
    transition: none;
  }
}
</style>
