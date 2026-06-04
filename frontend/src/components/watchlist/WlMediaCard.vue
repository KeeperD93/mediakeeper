<template>
  <div :id="'wl-card-' + item.tmdb_id + '_' + item.media_type" class="wlmc">
    <div class="wlmc-poster">
      <img
        v-if="item.poster"
        :src="item.poster"
        loading="lazy"
        @error="e => (e.target.style.display = 'none')"
      />
    </div>
    <div class="wlmc-info">
      <div class="wlmc-top">
        <div class="wlmc-titles">
          <p class="wlmc-name">{{ item.name }}</p>
          <p class="wlmc-meta">
            {{ isMovie(item) ? '🎬 ' + $t('common.film') : '📺 ' + $t('common.series') }} ·
            {{ item.year || '' }}
            <template v-if="isTv(item)">
              · {{ item.total_seasons || '?' }} {{ $t('common.seasons') }}
            </template>
          </p>
          <a :href="tmdbUrl" target="_blank" rel="noopener" class="wlmc-link" @click.stop>TMDB ↗</a>
        </div>
        <button
          class="wlmc-eye"
          :class="{ tracked: isT }"
          :title="isT ? $t('watchlist.unfollow') : $t('watchlist.follow')"
          @click.stop="toggleTrack(item)"
        >
          <!-- Open eye -->
          <Eye v-if="isT" class="w-5 h-5" />
          <!-- Closed eye -->
          <EyeOff v-else class="w-5 h-5" />
        </button>
      </div>
      <p v-if="item.overview" class="wlmc-synopsis">
        {{ item.overview.slice(0, 250) }}{{ item.overview.length > 250 ? '…' : '' }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWatchlist } from '@/composables/useWatchlist'
import { Eye, EyeOff } from 'lucide-vue-next'
import { isMovie, isTv } from '@/constants/media'
import { tmdbWebUrl } from '@/utils/tmdb'

const props = defineProps({ item: Object })
const { isTracked, toggleTrack } = useWatchlist()
const { locale } = useI18n()

const isT = computed(() => isTracked(props.item.tmdb_id, props.item.media_type))
const tmdbUrl = computed(() => tmdbWebUrl(props.item.media_type, props.item.tmdb_id, locale.value))
</script>

<style scoped>
.wlmc {
  display: flex;
  gap: 14px;
  padding: 14px;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  background: rgb(var(--accent-rgb), 0.03);
  backdrop-filter: blur(10px);
  animation: card-in var(--duration-slow) ease-out both;
}
@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.wlmc-poster {
  width: 76px;
  height: 108px;
  border-radius: var(--radius-btn);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-tertiary);
}
.wlmc-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wlmc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.wlmc-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.wlmc-titles {
  min-width: 0;
}
.wlmc-name {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wlmc-meta {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 2px;
}
.wlmc-link {
  font-size: var(--text-2xs);
  color: var(--accent-400);
  text-decoration: none;
}
.wlmc-link:hover {
  color: var(--accent-300);
}
.wlmc-eye {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  transition: all 0.25s;
  background: rgb(244, 63, 94, 0.12);
  color: rgb(244, 63, 94, 0.6);
}
.wlmc-eye.tracked {
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
}
.wlmc-eye:hover {
  transform: scale(1.1);
}
.wlmc-synopsis {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 8px;
  line-height: var(--lh-normal);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
