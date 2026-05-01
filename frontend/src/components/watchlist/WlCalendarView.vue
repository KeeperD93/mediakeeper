<template>
  <div>
    <div class="wlcal-nav">
      <button class="wlcal-arrow" @click="prevMonth">
        <ChevronLeft :size="16" />
      </button>
      <h3 class="wlcal-title">{{ monthNames[month-1] }} {{ year }}</h3>
      <button class="wlcal-arrow" @click="nextMonth">
        <ChevronRight :size="16" />
      </button>
    </div>

    <div v-if="calLoading" class="wlcal-center"><MkSpinner size="md" /></div>
    <div v-else>
      <div class="wlcal-header-row">
        <div v-for="d in dayNames" :key="d" class="wlcal-day-name">{{ d }}</div>
      </div>
      <div class="wlcal-grid" :class="{ 'wlcal-grid-mobile': isMobile }">
        <div v-for="i in startOffset" :key="'e'+i" class="wlcal-cell wlcal-empty"/>
        <div
          v-for="day in daysInMonth" :key="day"
          class="wlcal-cell"
          :class="{ today: isToday(day), 'has-events': dayItems(day).length > 0 }"
          @click="isMobile && dayItems(day).length ? openDayModal(day) : null"
        >
          <span class="wlcal-day-num" :class="{'today-num':isToday(day)}">{{ day }}</span>

          <!-- Mobile: show a compact dot with count -->
          <span v-if="isMobile && dayItems(day).length" class="wlcal-mobile-badge">
            {{ dayItems(day).length }}
          </span>

          <!-- Desktop: full item list -->
          <div v-else-if="!isMobile" class="wlcal-items">
            <div
              v-for="item in dayItems(day).slice(0,4)" :key="item.date+item.series_name+item.episode"
              class="wlcal-item"
              @click.stop="openItemPopup($event, item)"
            >
              <img v-if="item.poster" :src="item.poster" class="wlcal-item-poster" @error="e=>e.target.style.display='none'"/>
              <div class="wlcal-item-info">
                <span class="wlcal-item-name">{{ item.series_name }}</span>
                <span class="wlcal-item-ep">{{ item.is_movie ? $t('common.film') : 'S'+pad(item.season)+'E'+pad(item.episode) }}</span>
              </div>
            </div>
            <button v-if="dayItems(day).length>4" class="wlcal-overflow" @click="openDayModal(day)">
              {{ $t('watchlist.seeMore', { n: dayItems(day).length - 4 }) || `voir plus (+${dayItems(day).length-4})` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Item popup (inline, no modal) -->
    <Teleport to="body">
      <div v-if="popup.visible" class="wlcal-popup" :style="popup.style" @click.stop>
        <button class="wlcal-popup-close" @click="popup.visible=false">
          <X :size="12" />
        </button>
        <div class="wlcal-popup-body">
          <div class="wlcal-popup-poster">
            <img v-if="popup.item?.poster" :src="popup.item.poster" @error="e=>e.target.style.display='none'"/>
            <div v-else class="wlcal-popup-ph">{{ popup.item?.is_movie?'🎬':'📺' }}</div>
          </div>
          <div class="wlcal-popup-info">
            <div class="wlcal-popup-name">{{ popup.item?.series_name }}</div>
            <div class="wlcal-popup-ep">
              {{ popup.item?.is_movie ? $t('common.film') : ('S'+pad(popup.item?.season||0)+'E'+pad(popup.item?.episode||0)) }}
              {{ popup.item?.episode_name?' · '+popup.item.episode_name:'' }}
            </div>
            <div v-if="popup.item?.air_date||popup.item?.date" class="wlcal-popup-date">
              <Calendar :size="10" :stroke-width="1.8" />
              {{ formatFullDate(popup.item?.air_date||popup.item?.date) }}
            </div>
            <p v-if="popup.item?.overview" class="wlcal-popup-overview">{{ popup.item.overview }}</p>
            <p v-if="popup.item?.notes" class="wlcal-popup-notes">💬 {{ popup.item.notes }}</p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Day modal (overflow) -->
    <Teleport to="body">
      <div v-if="dayModalDate" class="wlcal-overlay" @click.self="dayModalDate=null">
        <div class="wlcal-modal">
          <div class="wlcal-modal-header">
            <span class="wlcal-modal-title">{{ formatDayTitle(dayModalDate) }}</span>
            <span class="wlcal-modal-count">{{ dayItems(dayModalDate).length }} {{ $t('watchlist.releases', dayItems(dayModalDate).length) }}</span>
            <button class="wlcal-modal-close" @click="dayModalDate=null">
              <X :size="14" />
            </button>
          </div>
          <div class="wlcal-modal-body">
            <div v-for="item in dayItems(dayModalDate)" :key="item.series_name+item.episode" class="wlcal-modal-item" @click="openItemPopup($event,item)">
              <img v-if="item.poster" :src="item.poster" class="wlcal-modal-poster"/>
              <div class="wlcal-modal-info">
                <p class="wlcal-modal-name">{{ item.series_name }}</p>
                <p class="wlcal-modal-ep">{{ item.is_movie ? $t('common.film') : 'S'+pad(item.season)+'E'+pad(item.episode) }}{{ item.episode_name?' · '+item.episode_name:'' }}</p>
              </div>
              <span class="wlcal-modal-badge" :class="item.source === TRAILER_SOURCE.TRACKED ? 'badge-tracked' : 'badge-emby'">{{ item.source === TRAILER_SOURCE.TRACKED ? $t('watchlist.source.tracked') : $t('watchlist.source.emby') }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Click outside popup -->
    <div v-if="popup.visible" class="wlcal-popup-backdrop" @click="popup.visible=false"/>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWatchlist } from '@/composables/useWatchlist'
import { Calendar, ChevronLeft, ChevronRight, X } from 'lucide-vue-next'
import { TRAILER_SOURCE } from '@/constants/trailers'
import MkSpinner from '@/components/common/MkSpinner.vue'
const { getCalendar, calVersion } = useWatchlist()
const { t } = useI18n()

const isMobile = ref(false)
function updateIsMobile() { isMobile.value = typeof window !== 'undefined' && window.innerWidth < 768 }

const monthNames = computed(() => Array.from({length: 12}, (_, i) => new Date(2000, i, 1).toLocaleDateString(undefined, {month: 'long'}).replace(/^./, c => c.toUpperCase())))
const dayNames = computed(() => { const days = []; for (let i = 1; i <= 7; i++) { const d = new Date(2018, 0, i); days.push(d.toLocaleDateString(undefined, {weekday: 'short'}).slice(0,3).toUpperCase()) }; return days })
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth()+1)
const calItems = ref([])
const calLoading = ref(true)
const dayModalDate = ref(null)
let navTimer = null

const popup = reactive({ visible:false, style:{}, item:null })

const daysInMonth = computed(() => new Date(year.value, month.value, 0).getDate())
const startOffset = computed(() => { const d=new Date(year.value,month.value-1,1).getDay(); return (d+6)%7 })
const todayStr = computed(() => { const n=new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}` })
const byDay = computed(() => { const map={}; for(const item of calItems.value){if(!map[item.date])map[item.date]=[]; map[item.date].push(item)}; return map })

function dateStr(day) { return `${year.value}-${String(month.value).padStart(2,'0')}-${String(day).padStart(2,'0')}` }
function dayItems(day) { return byDay.value[dateStr(day)]||[] }
function isToday(day) { return dateStr(day)===todayStr.value }
function pad(n) { return String(n).padStart(2,'0') }
function formatDayTitle(day) { return new Date(dateStr(day)).toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long',year:'numeric'}) }
function formatFullDate(d) { if(!d)return''; return new Date(d).toLocaleDateString(undefined,{day:'numeric',month:'long',year:'numeric'}) }
function openDayModal(day) { dayModalDate.value=day }

function openItemPopup(e, item) {
  const rect = e.currentTarget.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const popupH = 220
  const top = spaceBelow > popupH ? rect.bottom+6 : rect.top-popupH-6
  const left = Math.max(8, Math.min(rect.left, window.innerWidth-300))
  popup.item = item
  popup.style = { top: top+'px', left: left+'px' }
  popup.visible = true
}

async function loadMonth() {
  // Ne montrer le spinner que si pas encore de data
  if (!calItems.value.length) calLoading.value = true
  calItems.value = [...await getCalendar(year.value, month.value)]
  calLoading.value = false
  getCalendar(year.value, month.value===12?1:month.value+1)
  getCalendar(year.value, month.value===1?12:month.value-1)
}
function prevMonth() { month.value--; if(month.value<1){month.value=12;year.value--}; debounceLoad() }
function nextMonth() { month.value++; if(month.value>12){month.value=1;year.value++}; debounceLoad() }
function debounceLoad() { clearTimeout(navTimer); navTimer=setTimeout(loadMonth,150) }
onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  loadMonth()
})
onUnmounted(() => { window.removeEventListener('resize', updateIsMobile) })
onActivated(loadMonth)
// When a tracking changes, re-read the cache (already updated by the incremental scan)
watch(calVersion, loadMonth)
</script>

<style scoped>
.wlcal-nav { display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; }
.wlcal-title { font-size:var(--text-md); font-weight:var(--font-bold); color:var(--text-primary); }
.wlcal-arrow { width:34px; height:34px; border-radius:var(--radius-btn); display:flex; align-items:center; justify-content:center; background:var(--surface-2); border:.5px solid var(--border-strong); color:var(--text-secondary); cursor:pointer; transition:all var(--duration-fast); }
.wlcal-arrow:hover { background:rgba(255,255,255,.08); color:var(--text-primary); }
.wlcal-center { display:flex; justify-content:center; padding:48px; }
.wlcal-header-row { display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin-bottom:4px; }
.wlcal-day-name { text-align:center; font-size:var(--text-2xs); font-weight:var(--font-bold); color:var(--text-muted); letter-spacing:var(--tracking-widest); padding:5px 0; }
.wlcal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:4px; }
.wlcal-cell { min-height:100px; border-radius:var(--radius-btn); padding:7px; border:.5px solid rgba(255,255,255,.05); background:rgba(255,255,255,.02); }
.wlcal-cell.today { border-color:rgba(99,102,241,.35); background:rgba(99,102,241,.04); }
.wlcal-cell.wlcal-empty { border:none; background:transparent; min-height:0; }
.wlcal-day-num { font-size:var(--text-2xs); font-weight:var(--font-medium); color:var(--text-muted); display:block; margin-bottom:5px; }
.wlcal-day-num.today-num { color:var(--accent-400); }
.wlcal-items { display:flex; flex-direction:column; gap:3px; }
.wlcal-item { display:flex; align-items:center; gap:5px; padding:3px 5px; border-radius:5px; background:var(--surface-2); cursor:pointer; overflow:hidden; transition:background .1s; }
.wlcal-item:hover { background:rgba(99,102,241,.12); }
.wlcal-item-poster { width:18px; height:26px; object-fit:cover; border-radius:3px; flex-shrink:0; }
.wlcal-item-info { flex:1; min-width:0; }
.wlcal-item-name { font-size:var(--text-3xs); font-weight:var(--font-medium); color:var(--text-primary); display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.wlcal-item-ep { font-size:.55rem; color:var(--text-muted); }
.wlcal-overflow { font-size:var(--text-3xs); color:var(--accent-400); font-weight:var(--font-medium); background:transparent; border:none; cursor:pointer; padding:1px 4px; text-align:left; }

/* Popup */
.wlcal-popup-backdrop { position:fixed; inset:0; z-index:9998; }
.wlcal-popup { position:fixed; z-index:9999; width:290px; background:rgba(13,18,32,.98); border:.5px solid rgba(255,255,255,.12); border-radius:var(--radius-card); box-shadow:var(--shadow-lg); padding:14px; animation:pop-in .12s ease-out; }
@keyframes pop-in { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
.wlcal-popup-close { position:absolute; top:9px; right:9px; width:22px; height:22px; border-radius:var(--radius-sm); border:none; background:var(--surface-3); color:var(--text-muted); cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all var(--duration-fast); }
.wlcal-popup-close:hover { background:rgba(255,255,255,.1); color:#fff; }
.wlcal-popup-body { display:flex; gap:12px; }
.wlcal-popup-poster { width:60px; height:88px; border-radius:var(--radius-btn); overflow:hidden; flex-shrink:0; background:var(--surface-2); }
.wlcal-popup-poster img { width:100%; height:100%; object-fit:cover; }
.wlcal-popup-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:20px; opacity:.2; }
.wlcal-popup-info { flex:1; min-width:0; padding-right:16px; }
.wlcal-popup-name { font-size:var(--text-sm); font-weight:var(--font-bold); color:#fff; line-height:1.2; margin-bottom:3px; }
.wlcal-popup-ep { font-size:var(--text-2xs); font-family:'SF Mono',monospace; color:var(--accent-400); margin-bottom:4px; }
.wlcal-popup-date { display:flex; align-items:center; gap:4px; font-size:var(--text-3xs); color:var(--text-muted); margin-bottom:5px; }
.wlcal-popup-overview { font-size:var(--text-2xs); color:var(--text-secondary); line-height:var(--lh-normal); display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.wlcal-popup-notes { font-size:var(--text-2xs); color:var(--text-secondary); margin-top:4px; font-style:italic; }

/* Day modal */
.wlcal-overlay { position:fixed; inset:0; z-index:9991; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; padding:24px; }
.wlcal-modal { width:100%; max-width:480px; max-height:70vh; background:rgba(13,18,32,.98); border:.5px solid rgba(255,255,255,.1); border-radius:var(--radius-card); display:flex; flex-direction:column; overflow:hidden; box-shadow:0 20px 50px rgba(0,0,0,.5); }
.wlcal-modal-header { display:flex; align-items:center; gap:10px; padding:13px 16px; border-bottom:.5px solid var(--border-default); }
.wlcal-modal-title { font-size:var(--text-base); font-weight:var(--font-bold); color:var(--text-primary); flex:1; text-transform:capitalize; }
.wlcal-modal-count { font-size:var(--text-2xs); color:var(--text-muted); }
.wlcal-modal-close { width:26px; height:26px; border-radius:var(--radius-sm); border:none; background:transparent; color:var(--text-muted); cursor:pointer; display:flex; align-items:center; justify-content:center; }
.wlcal-modal-close:hover { background:var(--surface-3); color:#fff; }
.wlcal-modal-body { flex:1; overflow-y:auto; padding:10px 16px; }
.wlcal-modal-item { display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:.5px solid rgba(255,255,255,.05); cursor:pointer; transition:background .1s; border-radius:4px; }
.wlcal-modal-item:last-child { border-bottom:none; }
.wlcal-modal-item:hover { background:rgba(255,255,255,.03); }
.wlcal-modal-poster { width:34px; height:48px; object-fit:cover; border-radius:var(--radius-sm); flex-shrink:0; }
.wlcal-modal-info { flex:1; min-width:0; }
.wlcal-modal-name { font-size:var(--text-sm); font-weight:var(--font-medium); color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.wlcal-modal-ep { font-size:var(--text-2xs); color:var(--text-muted); }
.wlcal-modal-badge { font-size:var(--text-3xs); padding:2px 7px; border-radius:var(--radius-btn); flex-shrink:0; font-weight:var(--font-medium); }
.badge-tracked { background:rgba(var(--color-success-rgb), .12); color:var(--color-success); }
.badge-emby { background:rgba(var(--color-info-rgb), .12); color:var(--color-info); }

/* Mobile — compact calendar: each cell becomes a small tappable square with day number + event count */
@media (max-width: 767px) {
  .wlcal-header-row { gap: 2px; }
  .wlcal-day-name { font-size: .58rem; padding: 3px 0; }
  .wlcal-grid-mobile { gap: 2px; }
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
  .wlcal-grid-mobile .wlcal-cell.has-events { cursor: pointer; }
  .wlcal-grid-mobile .wlcal-cell.has-events:active { transform: scale(0.94); }
  .wlcal-grid-mobile .wlcal-day-num {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    margin-bottom: 0;
    color: var(--text-secondary);
  }
  .wlcal-grid-mobile .wlcal-day-num.today-num { color: var(--accent-400); font-weight: var(--font-extrabold); }
  .wlcal-mobile-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 16px;
    height: 16px;
    padding: 0 5px;
    border-radius: var(--radius-pill);
    background: rgba(var(--accent-rgb), 0.22);
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
