<template>
  <Teleport to="body">
    <div v-if="popup.visible" class="wlcal-popup" :style="popup.style" @click.stop>
      <button class="wlcal-popup-close" @click="$emit('close')">
        <X :size="12" />
      </button>
      <div class="wlcal-popup-body">
        <div class="wlcal-popup-poster">
          <img
            v-if="popup.item?.poster"
            :src="popup.item.poster"
            @error="e => (e.target.style.display = 'none')"
          />
          <div v-else class="wlcal-popup-ph">{{ popup.item?.is_movie ? '🎬' : '📺' }}</div>
        </div>
        <div class="wlcal-popup-info">
          <div class="wlcal-popup-name">{{ popup.item?.series_name }}</div>
          <div class="wlcal-popup-ep">
            {{
              popup.item?.is_movie
                ? $t('dashboard.movieRelease')
                : 'S' + pad(popup.item?.season || 0) + 'E' + pad(popup.item?.episode || 0)
            }}
            {{
              !popup.item?.is_movie && popup.item?.episode_name
                ? ' · ' + popup.item.episode_name
                : ''
            }}
          </div>
          <div v-if="popup.item?.air_date || popup.item?.date" class="wlcal-popup-date">
            <Calendar :size="10" :stroke-width="1.8" />
            {{ formatFullDate(popup.item?.air_date || popup.item?.date) }}
          </div>
          <p v-if="popup.item?.overview" class="wlcal-popup-overview">
            {{ popup.item.overview }}
          </p>
          <p v-if="popup.item?.notes" class="wlcal-popup-notes">💬 {{ popup.item.notes }}</p>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Click outside popup -->
  <div v-if="popup.visible" class="wlcal-popup-backdrop" @click="$emit('close')" />
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { Calendar, X } from 'lucide-vue-next'

defineProps({ popup: { type: Object, required: true } })
defineEmits(['close'])

const { locale } = useI18n()

function pad(n) {
  return String(n).padStart(2, '0')
}
function formatFullDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString(locale.value, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
</script>

<style scoped>
.wlcal-popup-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9998;
}
</style>

<style>
/* Non-scoped: <Teleport to="body"> escapes scoped data-v attributes.
   All selectors are prefixed with .wlcal-popup* to keep namespace unique. */
.wlcal-popup {
  position: fixed;
  z-index: 9999;
  width: 290px;
  background: var(--mk-chrome-bg);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-lg);
  padding: 14px;
  animation: pop-in 0.12s ease-out;
}
@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.wlcal-popup-close {
  position: absolute;
  top: 9px;
  right: 9px;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--surface-3);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}
.wlcal-popup-close:hover {
  background: rgb(255, 255, 255, 0.1);
  color: var(--text-primary);
}
.wlcal-popup-body {
  display: flex;
  gap: 12px;
}
.wlcal-popup-poster {
  width: 60px;
  height: 88px;
  border-radius: var(--radius-btn);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface-2);
}
.wlcal-popup-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wlcal-popup-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  opacity: 0.2;
}
.wlcal-popup-info {
  flex: 1;
  min-width: 0;
  padding-right: 16px;
}
.wlcal-popup-name {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1.2;
  margin-bottom: 3px;
}
.wlcal-popup-ep {
  font-size: var(--text-2xs);
  font-family: 'SF Mono', monospace;
  color: var(--accent-400);
  margin-bottom: 4px;
}
.wlcal-popup-date {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin-bottom: 5px;
}
.wlcal-popup-overview {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  line-height: var(--lh-normal);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.wlcal-popup-notes {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  margin-top: 4px;
  font-style: italic;
}
</style>
