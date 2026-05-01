<template>
  <div ref="rootRef" class="tl">
    <div v-if="timelineLoading" class="tl-empty"><div class="tl-spin"/></div>
    <div v-else-if="!entries.length" class="tl-empty">
      <p class="tl-empty-text">{{ $t('watchlist.noEpisodesOnPeriod') }}</p>
    </div>
    <template v-else>
      <div class="tl-outer">
        <!-- Scrollable timeline -->
        <div ref="scrollRef" class="tl-scroll">

          <div v-for="(e, i) in entries" :key="e.date" class="tl-row" :data-date="e.date">

            <!-- LEFT HALF -->
            <div class="tl-left" :class="{ active: isLeft(i) }">
              <template v-if="isLeft(i)">
                <div class="tl-left-cards">
                  <div v-for="item in e.items" :key="item._key" class="tl-card">
                    <img v-if="item.poster" class="tl-poster" :src="item.poster" loading="lazy" @error="e2=>e2.target.style.display='none'"/>
                    <div v-else class="tl-poster tl-poster-ph">{{ item.is_movie?'🎬':'📺' }}</div>
                    <div class="tl-info">
                      <div class="tl-name">{{ item.series_name }}</div>
                      <div class="tl-ep">{{ label(item) }}</div>
                    </div>
                  </div>
                </div>
                <div class="tl-left-pill">
                  <div class="tl-date" :class="dateCls(e)">
                    <span v-if="e.past && !e.today" class="tl-past">{{ $t('watchlist.past') }}</span>
                    {{ e.today ? $t('watchlist.today') : e.label }}
                  </div>
                </div>
              </template>
            </div>

            <!-- AXIS -->
            <div class="tl-axis">
              <div class="tl-bar"/>
              <div class="tl-dot" :class="{ 'tl-dot-now': e.today }"/>
              <div class="tl-bar"/>
            </div>

            <!-- RIGHT HALF -->
            <div class="tl-right" :class="{ active: !isLeft(i) }">
              <template v-if="!isLeft(i)">
                <div class="tl-right-pill">
                  <div class="tl-date" :class="dateCls(e)">
                    <span v-if="e.past && !e.today" class="tl-past">{{ $t('watchlist.past') }}</span>
                    {{ e.today ? $t('watchlist.today') : e.label }}
                  </div>
                </div>
                <div class="tl-right-cards">
                  <div v-for="item in e.items" :key="item._key" class="tl-card">
                    <img v-if="item.poster" class="tl-poster" :src="item.poster" loading="lazy" @error="e2=>e2.target.style.display='none'"/>
                    <div v-else class="tl-poster tl-poster-ph">{{ item.is_movie?'🎬':'📺' }}</div>
                    <div class="tl-info">
                      <div class="tl-name">{{ item.series_name }}</div>
                      <div class="tl-ep">{{ label(item) }}</div>
                    </div>
                  </div>
                </div>
              </template>
            </div>

          </div>
        </div>

        <!-- NAV -->
        <div class="tl-nav">
          <div class="tl-nav-list">
            <button class="tl-nav-item tl-nav-auj" @click="goToday">
              <span class="tl-nav-dot" aria-hidden="true" />
              {{ $t('watchlist.todayShort') }}
            </button>
            <div class="tl-nav-line"/>
            <button v-for="m in months" :key="m.k" class="tl-nav-item" :class="{ now: m.now }" @click="goMonth(m.first)">
              {{ m.s }}<span class="tl-nav-y">{{ m.y }}</span>
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWatchlist } from '@/composables/useWatchlist'

const { timelineItems, timelineLoading } = useWatchlist()
const { t } = useI18n()
const scrollRef = ref(null)
const rootRef = ref(null)
let scrolled = false

const isMobile = ref(false)
function updateIsMobile() { isMobile.value = typeof window !== 'undefined' && window.innerWidth < 768 }

const NOW = new Date().toISOString().slice(0,10)
const FROM = (() => { const d=new Date(); d.setMonth(d.getMonth()-6); return d.toISOString().slice(0,10) })()
const TO = (() => { const d=new Date(); d.setMonth(d.getMonth()+6); return d.toISOString().slice(0,10) })()

// Auto-scroll au first affichage
onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  nextTick(doAutoScroll)
})
onUnmounted(() => { window.removeEventListener('resize', updateIsMobile) })
onActivated(() => { goToday() })

// Scroll to today as soon as data arrives (first load)
watch(timelineLoading, (v) => {
  if (!v && !scrolled) nextTick(doAutoScroll)
})

function doAutoScroll() {
  if (scrolled) return
  const el = rootRef.value
  if (!el || el.offsetParent === null) return
  const r = el.getBoundingClientRect()
  if (!r.height || !r.width) return
  goToday()
  scrolled = true
}

function goToday() {
  const c = scrollRef.value; if(!c) return
  let t = c.querySelector(`[data-date="${NOW}"]`)
  if (!t) { let best=null,bd=Infinity; c.querySelectorAll('[data-date]').forEach(r=>{const d=Math.abs(new Date(r.dataset.date)-new Date(NOW));if(d<bd){bd=d;best=r}}); t=best }
  if (t) c.scrollTo({top:Math.max(0,t.offsetTop-c.clientHeight/3),behavior:scrolled?'smooth':'auto'})
}
function goMonth(d) {
  const c = scrollRef.value; if(!c) return
  const rows = Array.from(c.querySelectorAll('[data-date]'))
  const t = rows.find(r=>r.dataset.date>=d)||rows[rows.length-1]
  if (t) c.scrollTo({top:Math.max(0,t.offsetTop-70),behavior:'smooth'})
}

const entries = computed(()=>{
  const m={}
  for (const it of timelineItems.value) { if(it.date<FROM||it.date>TO)continue; (m[it.date]||(m[it.date]=[])).push(it) }
  if(!m[NOW]) m[NOW]=[]
  return Object.keys(m).sort().map(d=>{
    const dt=new Date(d+'T00:00:00')
    return { date:d, today:d===NOW, past:d<NOW, label:dt.toLocaleDateString(undefined,{day:'numeric',month:'long',year:'numeric'}), items:m[d] }
  })
})

function isLeft(i) { return !isMobile.value && i%2===0 }
function pad(n) { return String(n).padStart(2,'0') }
function label(it) { let s=it.is_movie?t('common.film'):'S'+pad(it.season)+'E'+pad(it.episode); if(it.episode_name)s+=' · '+it.episode_name; return s }
function dateCls(e) { return {'tl-date-now':e.today,'tl-date-past':e.past&&!e.today} }

const months = computed(()=>{
  const o=[],n=new Date()
  for(let i=-6;i<=6;i++){
    const d=new Date(n.getFullYear(),n.getMonth()+i,1)
    const k=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`
    const s=d.toLocaleDateString(undefined,{month:'short'}).replace('.','').toUpperCase()
    const y=String(d.getFullYear()).slice(2)
    let first=k+'-01'; for(const e of entries.value){if(e.date.startsWith(k)){first=e.date;break}}
    o.push({k,s,y,first,now:NOW.startsWith(k)})
  }
  return o
})
</script>

<style scoped>
.tl{min-height:300px}
.tl-empty{display:flex;justify-content:center;align-items:center;padding:60px}
.tl-empty-text{color:var(--text-muted);font-size:var(--text-sm)}
.tl-spin{width:24px;height:24px;border:2px solid var(--border);border-top-color:var(--accent-500);border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}

.tl-outer{display:flex;align-items:stretch}
.tl-scroll{flex:1;min-width:0;max-height:80vh;overflow-y:auto;overflow-x:hidden;padding:20px 0 60px;scrollbar-width:thin;scrollbar-color:rgba(99,102,241,.2) transparent}

.tl-row{display:grid;grid-template-columns:1fr 40px 1fr;min-height:48px}

.tl-left{min-width:0;overflow:hidden;padding:6px 0}
.tl-left.active{display:grid;grid-template-columns:1fr auto;gap:0;align-items:start}
.tl-left-cards{display:flex;flex-direction:column;gap:5px;padding-right:6px}
.tl-left-pill{display:flex;align-items:flex-start;padding:0 10px;padding-top:4px}

.tl-right{min-width:0;overflow:hidden;padding:6px 0}
.tl-right.active{display:grid;grid-template-columns:auto 1fr;gap:0;align-items:start}
.tl-right-pill{display:flex;align-items:flex-start;padding:0 10px;padding-top:4px}
.tl-right-cards{display:flex;flex-direction:column;gap:5px;padding-left:6px}

.tl-axis{display:flex;flex-direction:column;align-items:center}
.tl-bar{flex:1;width:3px;min-height:6px;background:rgba(99,102,241,.35)}
.tl-row:first-child .tl-bar:first-child{background:linear-gradient(to bottom,rgba(99,102,241,.05),rgba(99,102,241,.35))}
.tl-row:last-child .tl-bar:last-child{background:linear-gradient(to bottom,rgba(99,102,241,.35),rgba(99,102,241,.05))}
.tl-dot{width:12px;height:12px;border-radius:50%;background:rgba(99,102,241,.5);border:2.5px solid rgba(15,15,30,.9);flex-shrink:0;margin:-1px 0;z-index:2}
.tl-dot-now{width:16px;height:16px;background: var(--accent-400);border:3px solid rgba(99,102,241,.4);box-shadow:0 0 18px rgba(99,102,241,.6),0 0 40px rgba(99,102,241,.2);animation:glow 2.5s ease-in-out infinite;margin:-2px 0}
@keyframes glow{0%,100%{box-shadow:0 0 18px rgba(99,102,241,.6),0 0 40px rgba(99,102,241,.2)}50%{box-shadow:0 0 28px rgba(99,102,241,.8),0 0 56px rgba(99,102,241,.3)}}

.tl-date{font-size:var(--text-sm);font-weight:var(--font-bold);padding:4px 12px;border-radius:var(--radius-btn);background:rgba(99,102,241,.12);color: var(--accent-300);white-space:nowrap;letter-spacing:.3px}
.tl-date-now{background:linear-gradient(135deg,#6366f1,#7c3aed);color:#fff;font-size:var(--text-sm);padding:6px 16px;border-radius:var(--radius-btn);box-shadow:0 4px 20px rgba(99,102,241,.4)}
.tl-date-past{background:rgba(99,102,241,.07);color:rgba(165,180,252,.5)}
.tl-past{font-size:.5rem;font-weight:var(--font-extrabold);padding:1px 5px;border-radius:4px;background:rgba(var(--color-warning-rgb), .12);color:var(--color-warning);letter-spacing:.6px;margin-right:5px;vertical-align:middle;display:inline-block}

.tl-card{display:flex;align-items:center;gap:11px;padding:9px 14px;border-radius:var(--radius-card);background:var(--surface-2);backdrop-filter:var(--blur-sm);border:.5px solid var(--border-strong);transition:border-color var(--duration-fast),transform var(--duration-fast);cursor:default}
.tl-card:hover{border-color:rgba(99,102,241,.35);transform:translateY(-1px)}
.tl-poster{width:38px;height:56px;border-radius:var(--radius-sm);overflow:hidden;background:rgba(255,255,255,.05);flex-shrink:0;object-fit:cover}
.tl-poster-ph{display:flex;align-items:center;justify-content:center;font-size:14px;opacity:.3}
.tl-info{flex:1;min-width:0}
.tl-name{font-size:var(--text-sm);font-weight:var(--font-medium);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text-primary)}
.tl-ep{font-size:var(--text-2xs);color:var(--text-secondary);font-family:'SF Mono','Cascadia Mono',monospace;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.tl-nav{width:56px;flex-shrink:0;border-left:.5px solid var(--border-default)}
.tl-nav-list{position:sticky;top:0;display:flex;flex-direction:column;align-items:center;gap:1px;padding:6px 0;height:80vh;justify-content:center}
.tl-nav-auj{background:rgba(99,102,241,.15)!important;color: var(--accent-400)!important;border-radius:var(--radius-btn)!important;padding:6px 4px!important;gap:2px;font-size:.56rem!important;font-weight:var(--font-extrabold)!important}
.tl-nav-auj:hover{background:rgba(99,102,241,.25)!important}
.tl-nav-dot{width:5px;height:5px;border-radius:50%;background:currentColor}
.tl-nav-line{width:28px;height:1px;background:var(--surface-3);margin:4px 0}
.tl-nav-item{display:flex;flex-direction:column;align-items:center;gap:1px;padding:5px 4px;border:none;background:transparent;color:rgba(165,180,252,.3);font-weight:var(--font-bold);font-family:inherit;text-transform:uppercase;cursor:pointer;border-radius:var(--radius-sm);transition:all var(--duration-fast);width:48px;font-size:var(--text-3xs)}
.tl-nav-item:hover{background:rgba(99,102,241,.1);color: var(--accent-300)}
.tl-nav-item.now{background:rgba(99,102,241,.12);color: var(--accent-400)}
.tl-nav-y{font-size:.48rem;opacity:.5}

/* Mobile — single-column: axis on the left, pill + cards take full width */
@media(max-width:767px){
  .tl-row{grid-template-columns:28px 1fr;min-height:auto}
  .tl-left{display:none}
  .tl-right{padding:8px 0 8px 10px}
  .tl-right.active{display:flex;flex-direction:column;gap:6px}
  .tl-right-pill{padding:0 0 4px 0}
  .tl-right-cards{padding-left:0;gap:6px}
  .tl-card{padding:8px 10px;gap:10px}
  .tl-poster{width:40px;height:58px}
  .tl-info{min-width:0}
  .tl-name{
    font-size:var(--text-sm);
    white-space:normal;
    overflow:hidden;
    text-overflow:ellipsis;
    display:-webkit-box;
    -webkit-line-clamp:2;
    -webkit-box-orient:vertical;
    line-height:1.25;
  }
  .tl-ep{font-size:var(--text-2xs);white-space:normal;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical}
  .tl-date{font-size:var(--text-2xs);padding:3px 10px}
  .tl-nav{width:40px}
  .tl-nav-item{width:36px;padding:4px 2px;font-size:.52rem}
  .tl-nav-y{display:none}
}
</style>
