<template>
  <div class="wlsu-wall">
    <div
      v-for="item in tracked"
      :key="item.tmdb_id + '_' + item.media_type"
      class="wlsu-card"
      @click="$emit('select', item)"
    >
      <div class="wlsu-card-img">
        <img
          v-if="item.poster"
          :src="item.poster"
          loading="lazy"
          @error="e => (e.target.style.display = 'none')"
        />
        <div v-else class="wlsu-card-ph">{{ isMovie(item) ? '🎬' : '📺' }}</div>
      </div>
      <div class="wlsu-card-status" :class="statusClass(item)" />
      <div class="wlsu-card-overlay">
        <div class="wlsu-card-name">{{ item.name }}</div>
        <div class="wlsu-card-meta">
          {{ typeLabel(item) }}{{ item.year ? ' · ' + item.year : ''
          }}{{ item.total_seasons ? ' · S' + item.total_seasons : '' }}
        </div>
        <button class="wlsu-untrack-btn" @click.stop="$emit('untrack', item)">
          <EyeOff :size="11" />
          {{ $t('watchlist.unfollow') }}
        </button>
      </div>
    </div>
    <div class="wlsu-add-card" @click="$emit('open-add')">
      <Plus :size="22" class="wlsu-add-icon" />
      <span>{{ $t('common.add') }}</span>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { isMovie } from '@/constants/media'
import { EyeOff, Plus } from 'lucide-vue-next'

defineProps({ tracked: { type: Array, required: true } })
defineEmits(['select', 'untrack', 'open-add'])

const { t } = useI18n()

function statusClass(item) {
  if (item.status === 'ended') return 'status-ended'
  if (item.status === 'hiatus') return 'status-hiatus'
  return 'status-active'
}

function typeLabel(item) {
  return isMovie(item) ? t('common.film') : t('common.series')
}
</script>

<style scoped>
.wlsu-wall {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(clamp(108px, 30vw, 120px), 1fr));
  gap: 6px;
}
@media (min-width: 768px) {
  .wlsu-wall {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 8px;
  }
}
.wlsu-card {
  position: relative;
  aspect-ratio: 2/3;
  border-radius: var(--radius-btn);
  overflow: hidden;
  cursor: pointer;
  background: var(--surface-1);
  border: 0.5px solid var(--border-default);
  transition: all var(--duration-base);
}
.wlsu-card:hover {
  transform: translateY(-3px);
  border-color: rgb(99, 102, 241, 0.3);
  box-shadow: 0 12px 32px rgb(0, 0, 0, 0.4);
}
.wlsu-card:hover .wlsu-card-overlay {
  opacity: 1;
}
.wlsu-card-img {
  width: 100%;
  height: 100%;
}
.wlsu-card-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.wlsu-card-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  opacity: 0.15;
  background: rgb(255, 255, 255, 0.02);
}
.wlsu-card-status {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.status-active {
  background: #34d399;
  box-shadow: 0 0 6px #34d399;
}
.status-hiatus {
  background: var(--color-warning);
  box-shadow: 0 0 6px var(--color-warning);
}
.status-ended {
  background: rgb(156, 163, 175, 0.5);
}
.wlsu-card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgb(7, 11, 20, 0.97) 0%,
    rgb(7, 11, 20, 0.6) 50%,
    transparent 100%
  );
  opacity: 0;
  transition: opacity var(--duration-base);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 10px;
  gap: 4px;
}
.wlsu-card-name {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1.2;
}
.wlsu-card-meta {
  font-size: 0.58rem;
  color: rgb(255, 255, 255, 0.45);
}
.wlsu-untrack-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.58rem;
  padding: 3px 7px;
  border-radius: 5px;
  background: rgb(var(--color-error-rgb), 0.15);
  color: var(--color-error);
  border: none;
  cursor: pointer;
  font-family: inherit;
  margin-top: 4px;
  transition: background var(--duration-fast);
}
.wlsu-untrack-btn:hover {
  background: rgb(var(--color-error-rgb), 0.3);
}
.wlsu-add-card {
  aspect-ratio: 2/3;
  border-radius: var(--radius-btn);
  border: 1px dashed rgb(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: var(--text-2xs);
  transition: all var(--duration-fast);
  background: transparent;
}
.wlsu-add-card:hover {
  border-color: rgb(99, 102, 241, 0.35);
  color: var(--accent-400);
}
.wlsu-add-icon {
  opacity: 0.3;
}
</style>
