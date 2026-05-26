<template>
  <Teleport to="body">
    <div v-if="dayModalDate" class="wlcal-overlay" @click.self="$emit('close')">
      <div class="wlcal-modal">
        <div class="wlcal-modal-header">
          <span class="wlcal-modal-title">{{ formatDayTitle(dayModalDate) }}</span>
          <span class="wlcal-modal-count">
            {{ items.length }}
            {{ $t('watchlist.releases', items.length) }}
          </span>
          <button class="wlcal-modal-close" @click="$emit('close')">
            <X :size="14" />
          </button>
        </div>
        <div class="wlcal-modal-body">
          <div
            v-for="item in items"
            :key="item.series_name + item.episode"
            class="wlcal-modal-item"
            @click="$emit('open-item', $event, item)"
          >
            <img v-if="item.poster" :src="item.poster" class="wlcal-modal-poster" />
            <div class="wlcal-modal-info">
              <p class="wlcal-modal-name">{{ item.series_name }}</p>
              <p class="wlcal-modal-ep">
                {{
                  item.is_movie
                    ? $t('common.film')
                    : 'S' + pad(item.season) + 'E' + pad(item.episode)
                }}{{ item.episode_name ? ' · ' + item.episode_name : '' }}
              </p>
            </div>
            <span
              class="wlcal-modal-badge"
              :class="item.source === TRAILER_SOURCE.TRACKED ? 'badge-tracked' : 'badge-emby'"
            >
              {{
                item.source === TRAILER_SOURCE.TRACKED
                  ? $t('watchlist.source.tracked')
                  : $t('watchlist.source.emby')
              }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { TRAILER_SOURCE } from '@/constants/trailers'
import { X } from 'lucide-vue-next'

defineProps({
  dayModalDate: { type: [Number, String], default: null },
  items: { type: Array, default: () => [] },
  formatDayTitle: { type: Function, required: true },
})
defineEmits(['close', 'open-item'])

function pad(n) {
  return String(n).padStart(2, '0')
}
</script>

<style scoped>
.wlcal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9991;
  background: rgb(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.wlcal-modal {
  width: 100%;
  max-width: 480px;
  max-height: 70vh;
  background: rgb(13, 18, 32, 0.98);
  border: 0.5px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 50px rgb(0, 0, 0, 0.5);
}
.wlcal-modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 0.5px solid var(--border-default);
}
.wlcal-modal-title {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  flex: 1;
  text-transform: capitalize;
}
.wlcal-modal-count {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.wlcal-modal-close {
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.wlcal-modal-close:hover {
  background: var(--surface-3);
  color: var(--text-primary);
}
.wlcal-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px 16px;
}
.wlcal-modal-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 0.5px solid rgb(255, 255, 255, 0.05);
  cursor: pointer;
  transition: background 0.1s;
  border-radius: 4px;
}
.wlcal-modal-item:last-child {
  border-bottom: none;
}
.wlcal-modal-item:hover {
  background: var(--surface-1);
}
.wlcal-modal-poster {
  width: 34px;
  height: 48px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.wlcal-modal-info {
  flex: 1;
  min-width: 0;
}
.wlcal-modal-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wlcal-modal-ep {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.wlcal-modal-badge {
  font-size: var(--text-3xs);
  padding: 2px 7px;
  border-radius: var(--radius-btn);
  flex-shrink: 0;
  font-weight: var(--font-medium);
}
.badge-tracked {
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}
.badge-emby {
  background: rgb(var(--color-info-rgb), 0.12);
  color: var(--color-info);
}
</style>
