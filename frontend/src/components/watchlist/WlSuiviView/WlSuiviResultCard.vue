<template>
  <div class="wlsu-result-card">
    <div class="wlsu-result-poster">
      <img
        v-if="item.poster"
        :src="item.poster"
        loading="lazy"
        @error="e => (e.target.style.display = 'none')"
      />
      <div v-else class="wlsu-result-poster-ph">{{ isMovie(item) ? '🎬' : '📺' }}</div>
    </div>
    <div class="wlsu-result-info">
      <div class="wlsu-result-name">{{ item.name }}</div>
      <div class="wlsu-result-meta">
        <span class="wlsu-result-type">{{ typeLabel(item) }}</span>
        <span v-if="item.year">{{ item.year }}</span>
        <span v-if="item.vote_average" class="wlsu-result-rating">
          ⭐ {{ item.vote_average?.toFixed(1) }}
        </span>
      </div>
      <p v-if="item.overview" class="wlsu-result-overview">
        {{ item.overview.slice(0, 160) }}{{ item.overview.length > 160 ? '…' : '' }}
      </p>
    </div>
    <button
      class="wlsu-eye-btn"
      :class="{ tracked: tracked }"
      :title="tracked ? $t('watchlist.unfollow') : $t('watchlist.follow')"
      @click.stop="$emit('toggle-track', item)"
    >
      <EyeOff v-if="!tracked" :size="18" />
      <Eye v-else :size="18" />
    </button>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { isMovie } from '@/constants/media'
import { Eye, EyeOff } from 'lucide-vue-next'

defineProps({
  item: { type: Object, required: true },
  tracked: { type: Boolean, default: false },
})
defineEmits(['toggle-track'])

const { t } = useI18n()

function typeLabel(item) {
  return isMovie(item) ? t('common.film') : t('common.series')
}
</script>

<style scoped>
.wlsu-result-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-btn);
  background: var(--surface-1);
  border: 0.5px solid var(--border-default);
  transition: border-color var(--duration-fast);
  position: relative;
}
.wlsu-result-card:hover {
  border-color: rgb(99, 102, 241, 0.2);
  background: var(--surface-2);
}
.wlsu-result-poster {
  width: 54px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface-2);
}
.wlsu-result-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wlsu-result-poster-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  opacity: 0.2;
}
.wlsu-result-info {
  flex: 1;
  min-width: 0;
  padding-right: 44px;
}
.wlsu-result-name {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: 4px;
}
.wlsu-result-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 5px;
  flex-wrap: wrap;
}
.wlsu-result-type {
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  padding: 2px 6px;
  border-radius: 5px;
  background: rgb(99, 102, 241, 0.15);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.wlsu-result-meta span:not(.wlsu-result-type, .wlsu-result-rating) {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.wlsu-result-rating {
  font-size: var(--text-2xs);
  color: var(--color-warning);
}
.wlsu-result-overview {
  font-size: var(--text-2xs);
  color: var(--text-faint);
  line-height: var(--lh-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.wlsu-eye-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
  flex-shrink: 0;
  background: rgb(var(--color-error-rgb), 0.12);
  color: var(--color-error);
}
.wlsu-eye-btn:hover {
  transform: scale(1.1);
}
.wlsu-eye-btn.tracked {
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
}
.wlsu-eye-btn.tracked:hover {
  background: rgb(var(--color-success-rgb), 0.25);
}
</style>
