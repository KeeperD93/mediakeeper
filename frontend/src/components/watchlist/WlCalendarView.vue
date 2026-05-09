<template>
  <div>
    <div class="wlcal-nav">
      <button class="wlcal-arrow" @click="prevMonth">
        <ChevronLeft :size="16" />
      </button>
      <h3 class="wlcal-title">{{ monthNames[month - 1] }} {{ year }}</h3>
      <button class="wlcal-arrow" @click="nextMonth">
        <ChevronRight :size="16" />
      </button>
    </div>

    <div v-if="calLoading" class="wlcal-center"><MkSpinner size="md" /></div>
    <WlCalGrid
      v-else
      :day-names="dayNames"
      :start-offset="startOffset"
      :days-in-month="daysInMonth"
      :day-items="dayItems"
      :is-today="isToday"
      :is-mobile="isMobile"
      @open-day="openDayModal"
      @open-item="openItemPopup"
    />

    <WlCalItemPopup :popup="popup" @close="popup.visible = false" />

    <WlCalDayModal
      :day-modal-date="dayModalDate"
      :items="dayModalDate ? dayItems(dayModalDate) : []"
      :format-day-title="formatDayTitle"
      @close="dayModalDate = null"
      @open-item="openItemPopup"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, reactive, watch } from 'vue'
import { useWatchlist } from '@/composables/useWatchlist'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'
import WlCalGrid from './WlCalendarView/WlCalGrid.vue'
import WlCalItemPopup from './WlCalendarView/WlCalItemPopup.vue'
import WlCalDayModal from './WlCalendarView/WlCalDayModal.vue'
const { getCalendar, calVersion } = useWatchlist()

const isMobile = ref(false)
function updateIsMobile() {
  isMobile.value = typeof window !== 'undefined' && window.innerWidth < 768
}

const monthNames = computed(() =>
  Array.from({ length: 12 }, (_, i) =>
    new Date(2000, i, 1)
      .toLocaleDateString(undefined, { month: 'long' })
      .replace(/^./, c => c.toUpperCase()),
  ),
)
const dayNames = computed(() => {
  const days = []
  for (let i = 1; i <= 7; i++) {
    const d = new Date(2018, 0, i)
    days.push(d.toLocaleDateString(undefined, { weekday: 'short' }).slice(0, 3).toUpperCase())
  }
  return days
})
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const calItems = ref([])
const calLoading = ref(true)
const dayModalDate = ref(null)
let navTimer = null

const popup = reactive({ visible: false, style: {}, item: null })

const daysInMonth = computed(() => new Date(year.value, month.value, 0).getDate())
const startOffset = computed(() => {
  const d = new Date(year.value, month.value - 1, 1).getDay()
  return (d + 6) % 7
})
const todayStr = computed(() => {
  const n = new Date()
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
})
const byDay = computed(() => {
  const map = {}
  for (const item of calItems.value) {
    if (!map[item.date]) map[item.date] = []
    map[item.date].push(item)
  }
  return map
})

function dateStr(day) {
  return `${year.value}-${String(month.value).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}
function dayItems(day) {
  return byDay.value[dateStr(day)] || []
}
function isToday(day) {
  return dateStr(day) === todayStr.value
}
function formatDayTitle(day) {
  return new Date(dateStr(day)).toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
function openDayModal(day) {
  dayModalDate.value = day
}

function openItemPopup(e, item) {
  const rect = e.currentTarget.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const popupH = 220
  const top = spaceBelow > popupH ? rect.bottom + 6 : rect.top - popupH - 6
  const left = Math.max(8, Math.min(rect.left, window.innerWidth - 300))
  popup.item = item
  popup.style = { top: top + 'px', left: left + 'px' }
  popup.visible = true
}

async function loadMonth() {
  // Ne montrer le spinner que si pas encore de data
  if (!calItems.value.length) calLoading.value = true
  calItems.value = [...(await getCalendar(year.value, month.value))]
  calLoading.value = false
  getCalendar(year.value, month.value === 12 ? 1 : month.value + 1)
  getCalendar(year.value, month.value === 1 ? 12 : month.value - 1)
}
function prevMonth() {
  month.value--
  if (month.value < 1) {
    month.value = 12
    year.value--
  }
  debounceLoad()
}
function nextMonth() {
  month.value++
  if (month.value > 12) {
    month.value = 1
    year.value++
  }
  debounceLoad()
}
function debounceLoad() {
  clearTimeout(navTimer)
  navTimer = setTimeout(loadMonth, 150)
}
onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  loadMonth()
})
onUnmounted(() => {
  window.removeEventListener('resize', updateIsMobile)
})
onActivated(loadMonth)
// When a tracking changes, re-read the cache (already updated by the incremental scan)
watch(calVersion, loadMonth)
</script>

<style scoped>
.wlcal-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.wlcal-title {
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.wlcal-arrow {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-btn);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.wlcal-arrow:hover {
  background: rgb(255, 255, 255, 0.08);
  color: var(--text-primary);
}
.wlcal-center {
  display: flex;
  justify-content: center;
  padding: 48px;
}
</style>
