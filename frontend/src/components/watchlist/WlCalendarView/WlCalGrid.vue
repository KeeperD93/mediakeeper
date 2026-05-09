<template>
  <div>
    <div class="wlcal-header-row">
      <div v-for="d in dayNames" :key="d" class="wlcal-day-name">{{ d }}</div>
    </div>
    <div class="wlcal-grid" :class="{ 'wlcal-grid-mobile': isMobile }">
      <div v-for="i in startOffset" :key="'e' + i" class="wlcal-cell wlcal-empty" />
      <div
        v-for="day in daysInMonth"
        :key="day"
        class="wlcal-cell"
        :class="{ today: isToday(day), 'has-events': dayItems(day).length > 0 }"
        @click="isMobile && dayItems(day).length ? $emit('open-day', day) : null"
      >
        <span class="wlcal-day-num" :class="{ 'today-num': isToday(day) }">{{ day }}</span>

        <!-- Mobile: show a compact dot with count -->
        <span v-if="isMobile && dayItems(day).length" class="wlcal-mobile-badge">
          {{ dayItems(day).length }}
        </span>

        <!-- Desktop: full item list -->
        <div v-else-if="!isMobile" class="wlcal-items">
          <div
            v-for="item in dayItems(day).slice(0, 4)"
            :key="item.date + item.series_name + item.episode"
            class="wlcal-item"
            @click.stop="$emit('open-item', $event, item)"
          >
            <img
              v-if="item.poster"
              :src="item.poster"
              class="wlcal-item-poster"
              @error="e => (e.target.style.display = 'none')"
            />
            <div class="wlcal-item-info">
              <span class="wlcal-item-name">{{ item.series_name }}</span>
              <span class="wlcal-item-ep">
                {{
                  item.is_movie
                    ? $t('common.film')
                    : 'S' + pad(item.season) + 'E' + pad(item.episode)
                }}
              </span>
            </div>
          </div>
          <button
            v-if="dayItems(day).length > 4"
            class="wlcal-overflow"
            @click="$emit('open-day', day)"
          >
            {{
              $t('watchlist.seeMore', { n: dayItems(day).length - 4 }) ||
              `voir plus (+${dayItems(day).length - 4})`
            }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  dayNames: { type: Array, required: true },
  startOffset: { type: Number, required: true },
  daysInMonth: { type: Number, required: true },
  dayItems: { type: Function, required: true },
  isToday: { type: Function, required: true },
  isMobile: { type: Boolean, required: true },
})
defineEmits(['open-day', 'open-item'])

function pad(n) {
  return String(n).padStart(2, '0')
}
</script>

<style scoped>
.wlcal-header-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 4px;
}
.wlcal-day-name {
  text-align: center;
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--text-muted);
  letter-spacing: var(--tracking-widest);
  padding: 5px 0;
}
.wlcal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.wlcal-cell {
  min-height: 100px;
  border-radius: var(--radius-btn);
  padding: 7px;
  border: 0.5px solid rgb(255, 255, 255, 0.05);
  background: rgb(255, 255, 255, 0.02);
}
.wlcal-cell.today {
  border-color: rgb(99, 102, 241, 0.35);
  background: rgb(99, 102, 241, 0.04);
}
.wlcal-cell.wlcal-empty {
  border: none;
  background: transparent;
  min-height: 0;
}
.wlcal-day-num {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-muted);
  display: block;
  margin-bottom: 5px;
}
.wlcal-day-num.today-num {
  color: var(--accent-400);
}
.wlcal-items {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.wlcal-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 5px;
  border-radius: 5px;
  background: var(--surface-2);
  cursor: pointer;
  overflow: hidden;
  transition: background 0.1s;
}
.wlcal-item:hover {
  background: rgb(99, 102, 241, 0.12);
}
.wlcal-item-poster {
  width: 18px;
  height: 26px;
  object-fit: cover;
  border-radius: 3px;
  flex-shrink: 0;
}
.wlcal-item-info {
  flex: 1;
  min-width: 0;
}
.wlcal-item-name {
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wlcal-item-ep {
  font-size: 0.55rem;
  color: var(--text-muted);
}
.wlcal-overflow {
  font-size: var(--text-3xs);
  color: var(--accent-400);
  font-weight: var(--font-medium);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 1px 4px;
  text-align: left;
}

/* Mobile */
@media (max-width: 767px) {
  .wlcal-header-row {
    gap: 2px;
  }
  .wlcal-day-name {
    font-size: 0.58rem;
    padding: 3px 0;
  }
  .wlcal-grid-mobile {
    gap: 2px;
  }
  .wlcal-grid-mobile .wlcal-cell {
    min-height: 0;
    aspect-ratio: 1 / 1;
    padding: 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    cursor: default;
    -webkit-tap-highlight-color: transparent;
  }
  .wlcal-grid-mobile .wlcal-cell.has-events {
    cursor: pointer;
  }
  .wlcal-grid-mobile .wlcal-cell.has-events:active {
    transform: scale(0.94);
  }
  .wlcal-grid-mobile .wlcal-day-num {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    margin-bottom: 0;
    color: var(--text-secondary);
  }
  .wlcal-grid-mobile .wlcal-day-num.today-num {
    color: var(--accent-400);
    font-weight: var(--font-extrabold);
  }
  .wlcal-mobile-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 16px;
    height: 16px;
    padding: 0 5px;
    border-radius: var(--radius-pill);
    background: rgb(var(--accent-rgb), 0.22);
    color: var(--accent-300);
    font-size: var(--text-3xs);
    font-weight: var(--font-bold);
    line-height: var(--lh-tight);
  }
  .wlcal-grid-mobile .wlcal-cell.today .wlcal-mobile-badge {
    background: var(--accent-500);
    color: #fff;
  }
}
</style>
