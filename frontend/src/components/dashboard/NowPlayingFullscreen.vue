<template>
  <Teleport to="body">
    <transition name="np-fade">
      <div v-if="visible" class="np-overlay" @click.self="$emit('close')">
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
        <button
          class="np-close"
          type="button"
          :aria-label="$t('common.close')"
          @click="$emit('close')"
        >
          <X :size="14" />
        </button>

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

            <h1 class="np-title">{{ session.series || session.media }}</h1>
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
                <span v-if="tmdbData.runtime" class="np-chip">{{ tmdbData.runtime }} min</span>
                <span v-if="tmdbData.seasons_count" class="np-chip">
                  {{ tmdbData.seasons_count }} saison{{ tmdbData.seasons_count > 1 ? 's' : '' }}
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
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  session: { type: Object, default: () => ({}) },
})
defineEmits(['close'])

const { apiGet } = useApi()
const tmdbData = ref(null)
const tmdbLoading = ref(false)
const cache = {}

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
        const detail = await apiGet(`/api/watchlist/tmdb/${results[0].type}/${results[0].id}`)
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

.np-close {
  position: absolute;
  top: 24px;
  right: 28px;
  z-index: 10;
  background: rgb(255, 255, 255, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgb(255, 255, 255, 0.15);
  border-radius: 50%;
  color: rgb(255, 255, 255, 0.7);
  font-size: 20px;
  width: 44px;
  height: 44px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}
.np-close:hover {
  background: rgb(255, 255, 255, 0.2);
  color: var(--text-primary);
}

.np-content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  gap: 40px;
  max-width: 900px;
  padding: 48px;
}

.np-poster {
  width: 220px;
  height: 330px;
  border-radius: var(--radius-card);
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: var(--shadow-lg);
  border: 1px solid rgb(255, 255, 255, 0.1);
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
  gap: 8px;
  margin-bottom: 8px;
}
.np-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.np-dot-green {
  background: #22c55e;
  box-shadow: 0 0 8px rgb(34, 197, 94, 0.5);
}
.np-dot-yellow {
  background: #facc15;
  box-shadow: 0 0 8px rgb(250, 204, 21, 0.5);
}
.np-badge-label {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgb(255, 255, 255, 0.6);
}

.np-title {
  font-size: 36px;
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0 0 6px;
  line-height: 1.2;
}
.np-sub {
  font-size: var(--text-md);
  color: rgb(255, 255, 255, 0.45);
  margin: 0 0 16px;
}

.np-user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.np-user-label {
  font-size: var(--text-base);
  color: rgb(255, 255, 255, 0.7);
  font-weight: var(--font-regular);
}
.np-device {
  font-size: var(--text-xs);
  color: rgb(255, 255, 255, 0.3);
}

.np-progress-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.np-progress-bg {
  flex: 1;
  height: 5px;
  background: rgb(255, 255, 255, 0.1);
  border-radius: 3px;
  max-width: 350px;
}
.np-progress-fill {
  height: 5px;
  background: linear-gradient(90deg, #6366f1, #818cf8);
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
  animation: np-info-in 0.4s ease-out 0.4s both;
}
.np-tmdb-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.np-chip {
  font-size: var(--text-xs);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-3);
  color: rgb(255, 255, 255, 0.5);
}
.np-chip-vote {
  background: rgb(250, 204, 21, 0.12);
  color: #facc15;
}
.np-genres {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 14px;
}
.np-genre {
  font-size: var(--text-2xs);
  padding: 3px 10px;
  border-radius: 4px;
  background: rgb(99, 102, 241, 0.15);
  color: var(--accent-400);
}
.np-overview {
  font-size: var(--text-base);
  color: rgb(255, 255, 255, 0.45);
  line-height: 1.7;
  margin: 0;
  max-height: 120px;
  overflow-y: auto;
}
.np-tmdb-loading {
  font-size: var(--text-xs);
  color: var(--text-very-faint);
}

.np-overview::-webkit-scrollbar {
  width: 3px;
}
.np-overview::-webkit-scrollbar-thumb {
  background: rgb(255, 255, 255, 0.1);
  border-radius: 2px;
}

@media (max-width: 768px) {
  .np-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 24px;
    gap: 24px;
  }
  .np-poster {
    width: 160px;
    height: 240px;
  }
  .np-title {
    font-size: 24px;
  }
  .np-progress-wrap {
    justify-content: center;
  }
}
</style>
