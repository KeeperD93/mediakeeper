<template>
  <div class="pt-calendar">
    <div class="pt-cal-header">
      <h2>{{ $t('portal.calendar.title') }}</h2>
      <div class="pt-cal-nav">
        <button @click="prevMonth">‹</button>
        <span>{{ monthLabel }}</span>
        <button @click="nextMonth">›</button>
      </div>
    </div>

    <div class="pt-cal-grid">
      <div v-for="day in ['L', 'M', 'M', 'J', 'V', 'S', 'D']" :key="day" class="pt-cal-day-header">
        {{ day }}
      </div>
      <div
        v-for="cell in calendarCells"
        :key="cell.key"
        class="pt-cal-cell"
        :class="{ 'pt-cal-today': cell.isToday, 'pt-cal-empty': !cell.day }"
      >
        <span v-if="cell.day" class="pt-cal-num">{{ cell.day }}</span>
        <div
          v-for="item in cell.items"
          :key="item.id"
          class="pt-cal-item"
          @click="$emit('select', item)"
        >
          <img
            v-if="item.poster_url"
            :src="item.poster_url"
            :alt="item.title"
            class="pt-cal-poster"
            loading="lazy"
          />
          <span class="pt-cal-item-title">{{ item.title }}</span>
        </div>
      </div>
    </div>

    <h3 class="pt-section-title">{{ $t('portal.calendar.reminders') }}</h3>
    <div v-for="r in reminders" :key="r.tmdb_id" class="pt-reminder-row">
      <span>{{ isMovie(r) ? '🎬' : '📺' }}</span>
      <span class="pt-reminder-title">TMDB #{{ r.tmdb_id }}</span>
      <span class="pt-reminder-date">
        {{ r.release_date ? new Date(r.release_date).toLocaleDateString() : '—' }}
      </span>
      <button class="pt-icon-btn" @click="removeRem(r.tmdb_id)"><i class="icon-x" /></button>
    </div>
    <div v-if="!reminders.length" class="pt-empty">{{ $t('portal.calendar.noReminders') }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { usePortalSocial } from '@/composables/portal/usePortalSocial'
import { isMovie } from '@/constants/media'

defineEmits(['select'])

const { apiGet } = useApi()
const { reminders, fetchReminders, removeReminder } = usePortalSocial()

const currentMonth = ref(new Date())
const upcomingItems = ref([])

const monthLabel = computed(() => {
  const d = currentMonth.value
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
})

const calendarCells = computed(() => {
  const d = currentMonth.value
  const year = d.getFullYear()
  const month = d.getMonth()
  const firstDay = (new Date(year, month, 1).getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const today = new Date()
  const cells = []

  for (let i = 0; i < firstDay; i++) {
    cells.push({ key: `e${i}`, day: null, items: [], isToday: false })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    const items = upcomingItems.value.filter(item => item.release_date?.startsWith(dateStr))
    const isToday =
      today.getFullYear() === year && today.getMonth() === month && today.getDate() === day
    cells.push({ key: `d${day}`, day, items, isToday })
  }
  return cells
})

function prevMonth() {
  const d = new Date(currentMonth.value)
  d.setMonth(d.getMonth() - 1)
  currentMonth.value = d
}
function nextMonth() {
  const d = new Date(currentMonth.value)
  d.setMonth(d.getMonth() + 1)
  currentMonth.value = d
}
async function removeRem(tmdbId) {
  await removeReminder(tmdbId)
  await fetchReminders()
}

onMounted(async () => {
  const [res] = await Promise.all([
    apiGet('/api/portal/catalog/upcoming').catch(() => null),
    fetchReminders(),
  ])
  if (res) {
    upcomingItems.value = (res.items || []).map(item => ({
      ...item,
      release_date: item.year ? `${item.year}-01-01` : null,
    }))
  }
})
</script>

<style scoped>
.pt-calendar {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
}
.pt-cal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.pt-cal-header h2 {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-cal-nav {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.pt-cal-nav button {
  background: none;
  border: none;
  color: var(--accent);
  font-size: var(--portal-text-xl);
  cursor: pointer;
}
.pt-cal-nav span {
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
  min-width: 150px;
  text-align: center;
}
.pt-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: var(--border);
  border-radius: var(--radius-card);
  overflow: hidden;
  margin-bottom: 2rem;
}
.pt-cal-day-header {
  background: var(--bg-tertiary);
  padding: 0.5rem;
  text-align: center;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  color: var(--text-muted);
}
.pt-cal-cell {
  background: var(--bg-secondary);
  min-height: 80px;
  padding: 0.3rem;
}
.pt-cal-empty {
  background: var(--bg-primary);
}
.pt-cal-today {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.pt-cal-num {
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  color: var(--text-muted);
}
.pt-cal-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  margin-top: 0.2rem;
}
.pt-cal-poster {
  width: 20px;
  height: 30px;
  border-radius: 2px;
  object-fit: cover;
}
.pt-cal-item-title {
  font-size: var(--portal-text-3xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pt-section-title {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}
.pt-reminder-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border);
}
.pt-reminder-title {
  flex: 1;
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
  font-size: var(--portal-text-base);
}
.pt-reminder-date {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}
.pt-icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 1rem 0;
  font-size: var(--portal-text-sm);
}
</style>
