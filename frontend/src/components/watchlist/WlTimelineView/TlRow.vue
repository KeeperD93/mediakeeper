<template>
  <div class="tl-row" :data-date="entry.date">
    <!-- LEFT HALF -->
    <div class="tl-left" :class="{ active: leftActive }">
      <template v-if="leftActive">
        <div class="tl-left-cards">
          <div v-for="item in entry.items" :key="item._key" class="tl-card">
            <img
              v-if="item.poster"
              class="tl-poster"
              :src="item.poster"
              loading="lazy"
              @error="e2 => (e2.target.style.display = 'none')"
            />
            <div v-else class="tl-poster tl-poster-ph">
              {{ item.is_movie ? '🎬' : '📺' }}
            </div>
            <div class="tl-info">
              <div class="tl-name">{{ item.series_name }}</div>
              <div class="tl-ep">{{ label(item) }}</div>
            </div>
          </div>
        </div>
        <div class="tl-left-pill">
          <div class="tl-date" :class="dateCls(entry)">
            <span v-if="entry.past && !entry.today" class="tl-past">
              {{ $t('watchlist.past') }}
            </span>
            {{ entry.today ? $t('watchlist.today') : entry.label }}
          </div>
        </div>
      </template>
    </div>

    <!-- AXIS -->
    <div class="tl-axis">
      <div class="tl-bar" />
      <div class="tl-dot" :class="{ 'tl-dot-now': entry.today }" />
      <div class="tl-bar" />
    </div>

    <!-- RIGHT HALF -->
    <div class="tl-right" :class="{ active: !leftActive }">
      <template v-if="!leftActive">
        <div class="tl-right-pill">
          <div class="tl-date" :class="dateCls(entry)">
            <span v-if="entry.past && !entry.today" class="tl-past">
              {{ $t('watchlist.past') }}
            </span>
            {{ entry.today ? $t('watchlist.today') : entry.label }}
          </div>
        </div>
        <div class="tl-right-cards">
          <div v-for="item in entry.items" :key="item._key" class="tl-card">
            <img
              v-if="item.poster"
              class="tl-poster"
              :src="item.poster"
              loading="lazy"
              @error="e2 => (e2.target.style.display = 'none')"
            />
            <div v-else class="tl-poster tl-poster-ph">
              {{ item.is_movie ? '🎬' : '📺' }}
            </div>
            <div class="tl-info">
              <div class="tl-name">{{ item.series_name }}</div>
              <div class="tl-ep">{{ label(item) }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  entry: { type: Object, required: true },
  leftActive: { type: Boolean, required: true },
})

const { t } = useI18n()

function pad(n) {
  return String(n).padStart(2, '0')
}
function label(it) {
  let s = it.is_movie ? t('common.film') : 'S' + pad(it.season) + 'E' + pad(it.episode)
  if (it.episode_name) s += ' · ' + it.episode_name
  return s
}
function dateCls(e) {
  return { 'tl-date-now': e.today, 'tl-date-past': e.past && !e.today }
}
</script>

<style scoped>
.tl-row {
  display: grid;
  grid-template-columns: 1fr 40px 1fr;
  min-height: 48px;
}

.tl-left {
  min-width: 0;
  overflow: hidden;
  padding: 6px 0;
}
.tl-left.active {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0;
  align-items: start;
}
.tl-left-cards {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-right: 6px;
}
.tl-left-pill {
  display: flex;
  align-items: flex-start;
  padding: 0 10px;
  padding-top: 4px;
}

.tl-right {
  min-width: 0;
  overflow: hidden;
  padding: 6px 0;
}
.tl-right.active {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0;
  align-items: start;
}
.tl-right-pill {
  display: flex;
  align-items: flex-start;
  padding: 0 10px;
  padding-top: 4px;
}
.tl-right-cards {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-left: 6px;
}

.tl-axis {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.tl-bar {
  flex: 1;
  width: 3px;
  min-height: 6px;
  background: rgb(99, 102, 241, 0.35);
}
.tl-row:first-child .tl-bar:first-child {
  background: linear-gradient(to bottom, rgb(99, 102, 241, 0.05), rgb(99, 102, 241, 0.35));
}
.tl-row:last-child .tl-bar:last-child {
  background: linear-gradient(to bottom, rgb(99, 102, 241, 0.35), rgb(99, 102, 241, 0.05));
}
.tl-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgb(99, 102, 241, 0.5);
  border: 2.5px solid rgb(15, 15, 30, 0.9);
  flex-shrink: 0;
  margin: -1px 0;
  z-index: 2;
}
.tl-dot-now {
  width: 16px;
  height: 16px;
  background: var(--accent-400);
  border: 3px solid rgb(99, 102, 241, 0.4);
  box-shadow:
    0 0 18px rgb(99, 102, 241, 0.6),
    0 0 40px rgb(99, 102, 241, 0.2);
  animation: glow 2.5s ease-in-out infinite;
  margin: -2px 0;
}
@keyframes glow {
  0%,
  100% {
    box-shadow:
      0 0 18px rgb(99, 102, 241, 0.6),
      0 0 40px rgb(99, 102, 241, 0.2);
  }
  50% {
    box-shadow:
      0 0 28px rgb(99, 102, 241, 0.8),
      0 0 56px rgb(99, 102, 241, 0.3);
  }
}

.tl-date {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  padding: 4px 12px;
  border-radius: var(--radius-btn);
  background: rgb(99, 102, 241, 0.12);
  color: var(--accent-300);
  white-space: nowrap;
  letter-spacing: 0.3px;
}
.tl-date-now {
  background: linear-gradient(135deg, #6366f1, #7c3aed);
  color: var(--text-primary);
  font-size: var(--text-sm);
  padding: 6px 16px;
  border-radius: var(--radius-btn);
  box-shadow: 0 4px 20px rgb(99, 102, 241, 0.4);
}
.tl-date-past {
  background: rgb(99, 102, 241, 0.07);
  color: rgb(165, 180, 252, 0.5);
}
.tl-past {
  font-size: 0.5rem;
  font-weight: var(--font-extrabold);
  padding: 1px 5px;
  border-radius: 4px;
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
  letter-spacing: 0.6px;
  margin-right: 5px;
  vertical-align: middle;
  display: inline-block;
}

.tl-card {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 14px;
  border-radius: var(--radius-card);
  background: var(--surface-2);
  backdrop-filter: var(--blur-sm);
  border: 0.5px solid var(--border-strong);
  transition:
    border-color var(--duration-fast),
    transform var(--duration-fast);
  cursor: default;
}
.tl-card:hover {
  border-color: rgb(99, 102, 241, 0.35);
  transform: translateY(-1px);
}
.tl-poster {
  width: 38px;
  height: 56px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
  flex-shrink: 0;
  object-fit: cover;
}
.tl-poster-ph {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0.3;
}
.tl-info {
  flex: 1;
  min-width: 0;
}
.tl-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
}
.tl-ep {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Mobile — single-column: axis on the left, pill + cards take full width */
@media (max-width: 767px) {
  .tl-row {
    grid-template-columns: 28px 1fr;
    min-height: auto;
  }
  .tl-left {
    display: none;
  }
  .tl-right {
    padding: 8px 0 8px 10px;
  }
  .tl-right.active {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .tl-right-pill {
    padding: 0 0 4px;
  }
  .tl-right-cards {
    padding-left: 0;
    gap: 6px;
  }
  .tl-card {
    padding: 8px 10px;
    gap: 10px;
  }
  .tl-poster {
    width: 40px;
    height: 58px;
  }
  .tl-info {
    min-width: 0;
  }
  .tl-name {
    font-size: var(--text-sm);
    white-space: normal;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    line-height: 1.25;
  }
  .tl-ep {
    font-size: var(--text-2xs);
    white-space: normal;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }
  .tl-date {
    font-size: var(--text-2xs);
    padding: 3px 10px;
  }
}
</style>
