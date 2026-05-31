<template>
  <Teleport to="body">
    <div v-if="selected" class="wlsu-detail-overlay" @click.self="$emit('close')">
      <div class="wlsu-detail">
        <button class="wlsu-detail-close" @click="$emit('close')">
          <X :size="14" />
        </button>
        <div class="wlsu-detail-body">
          <div class="wlsu-detail-poster">
            <img
              v-if="selected.poster"
              :src="selected.poster"
              @error="e => (e.target.style.display = 'none')"
            />
            <div v-else class="wlsu-detail-ph">{{ isMovie(selected) ? '🎬' : '📺' }}</div>
          </div>
          <div class="wlsu-detail-info">
            <div class="wlsu-detail-title">{{ selected.name }}</div>
            <div class="wlsu-detail-meta">
              <span>{{ typeLabel(selected) }}</span>
              <span v-if="selected.year">{{ selected.year }}</span>
              <span v-if="selected.total_seasons">
                {{ selected.total_seasons }}
                {{ $t('common.season', selected.total_seasons).toLowerCase() }}
              </span>
            </div>
            <p v-if="selected.overview" class="wlsu-detail-overview">{{ selected.overview }}</p>
            <a
              :href="
                'https://www.themoviedb.org/' +
                (selected.media_type || 'tv') +
                '/' +
                selected.tmdb_id
              "
              target="_blank"
              rel="noopener"
              class="wlsu-tmdb-link"
            >
              TMDB ↗
            </a>
            <button class="wlsu-untrack-btn-lg" @click="$emit('untrack', selected)">
              <EyeOff :size="13" />
              {{ $t('watchlist.unfollow') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { isMovie } from '@/constants/media'
import { EyeOff, X } from 'lucide-vue-next'

defineProps({ selected: { type: Object, default: null } })
defineEmits(['close', 'untrack'])

const { t } = useI18n()

function typeLabel(item) {
  return isMovie(item) ? t('common.film') : t('common.series')
}
</script>

<style scoped>
.wlsu-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 9990;
  background: rgb(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.wlsu-detail {
  width: 100%;
  max-width: 520px;
  background: rgb(13, 18, 32, 0.98);
  border: 0.5px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-card);
  overflow: hidden;
  position: relative;
  box-shadow: var(--shadow-xl);
}
.wlsu-detail-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--surface-3);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
  z-index: 1;
}
.wlsu-detail-close:hover {
  background: rgb(255, 255, 255, 0.1);
  color: var(--text-primary);
}
.wlsu-detail-body {
  display: flex;
  gap: 16px;
  padding: 20px;
}
.wlsu-detail-poster {
  width: 100px;
  height: 148px;
  border-radius: var(--radius-btn);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface-2);
}
.wlsu-detail-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wlsu-detail-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  opacity: 0.2;
}
.wlsu-detail-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-right: 24px;
}
.wlsu-detail-title {
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.wlsu-detail-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.wlsu-detail-meta span {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  background: var(--surface-2);
  padding: 2px 7px;
  border-radius: 5px;
}
.wlsu-detail-overview {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: var(--lh-relaxed);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.wlsu-tmdb-link {
  font-size: var(--text-2xs);
  color: var(--accent-400);
  text-decoration: none;
}
.wlsu-untrack-btn-lg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-btn);
  background: rgb(var(--color-error-rgb), 0.1);
  color: var(--color-error);
  border: 0.5px solid rgb(var(--color-error-rgb), 0.2);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  font-family: inherit;
  margin-top: 4px;
  transition: all var(--duration-fast);
}
.wlsu-untrack-btn-lg:hover {
  background: rgb(var(--color-error-rgb), 0.25);
}
</style>
