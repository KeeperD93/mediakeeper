<template>
  <div>
    <div class="wlsu-header">
      <div class="wlsu-section-label">{{ $t('watchlist.trackedCount', { count: tracked.length }) }}</div>
      <div class="wlsu-view-toggle">
        <button class="vt-btn" :class="{active:viewMode==='wall'}" :title="$t('watchlist.posterWall')" @click="viewMode='wall'">
          <LayoutGrid :size="12" />
        </button>
        <button class="vt-btn" :class="{active:viewMode==='list'}" :title="$t('watchlist.listView')" @click="viewMode='list'">
          <List :size="12" />
        </button>
      </div>
    </div>

    <p v-if="!tracked.length && viewMode==='list'" class="wlsu-empty">{{ $t('watchlist.noTracked') }}</p>

    <div v-if="viewMode==='wall'" class="wlsu-wall">
      <div v-for="item in tracked" :key="item.tmdb_id+'_'+item.media_type" class="wlsu-card" @click="selected=item">
        <div class="wlsu-card-img">
          <img v-if="item.poster" :src="item.poster" loading="lazy" @error="e=>e.target.style.display='none'"/>
          <div v-else class="wlsu-card-ph">{{ isMovie(item)?'🎬':'📺' }}</div>
        </div>
        <div class="wlsu-card-status" :class="statusClass(item)"/>
        <div class="wlsu-card-overlay">
          <div class="wlsu-card-name">{{ item.name }}</div>
          <div class="wlsu-card-meta">{{ typeLabel(item) }}{{ item.year?' · '+item.year:'' }}{{ item.total_seasons?' · S'+item.total_seasons:'' }}</div>
          <button class="wlsu-untrack-btn" @click.stop="toggleTrack(item)">
            <EyeOff :size="11" />
            {{ $t('watchlist.unfollow') }}
          </button>
        </div>
      </div>
      <div class="wlsu-add-card" @click="openAddModal">
        <Plus :size="22" class="wlsu-add-icon" />
        <span>{{ $t('common.add') }}</span>
      </div>
    </div>

    <div v-else class="wlsu-list-view">
      <WlMediaCard v-for="item in tracked" :key="item.tmdb_id+'_'+item.media_type" :item="item"/>
      <div class="wlsu-add-list" @click="openAddModal">
        <Plus :size="14" />
        {{ $t('watchlist.addMovieOrSeries') }}
      </div>
    </div>

    <Teleport to="body">
      <div v-if="selected" class="wlsu-detail-overlay" @click.self="selected=null">
        <div class="wlsu-detail">
          <button class="wlsu-detail-close" @click="selected=null">
            <X :size="14" />
          </button>
          <div class="wlsu-detail-body">
            <div class="wlsu-detail-poster">
              <img v-if="selected.poster" :src="selected.poster" @error="e=>e.target.style.display='none'"/>
              <div v-else class="wlsu-detail-ph">{{ isMovie(selected)?'🎬':'📺' }}</div>
            </div>
            <div class="wlsu-detail-info">
              <div class="wlsu-detail-title">{{ selected.name }}</div>
              <div class="wlsu-detail-meta">
                <span>{{ typeLabel(selected) }}</span>
                <span v-if="selected.year">{{ selected.year }}</span>
                <span v-if="selected.total_seasons">{{ selected.total_seasons }} {{ $t('common.season', selected.total_seasons).toLowerCase() }}</span>
              </div>
              <p v-if="selected.overview" class="wlsu-detail-overview">{{ selected.overview }}</p>
              <a :href="'https://www.themoviedb.org/'+(selected.media_type||'tv')+'/'+selected.tmdb_id" target="_blank" rel="noopener" class="wlsu-tmdb-link">TMDB ↗</a>
              <button class="wlsu-untrack-btn-lg" @click="toggleTrack(selected);selected=null">
                <EyeOff :size="13" />
                {{ $t('watchlist.unfollow') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showAddModal" class="wlsu-add-overlay" @click.self="closeAddModal">
        <div class="wlsu-add-modal">
          <div class="wlsu-add-header">
            <span class="wlsu-add-title">{{ $t('watchlist.addContent') }}</span>
            <button class="wlsu-add-close" @click="closeAddModal">
              <X :size="14" />
            </button>
          </div>
          <div class="wlsu-add-search-wrap">
            <Search :size="15" class="wlsu-search-icon" />
            <input ref="searchInput" v-model="addQuery" type="text" :placeholder="$t('watchlist.searchMovieOrSeries')" class="wlsu-add-input" @input="onAddSearch"/>
            <div v-if="addSearching" class="wlsu-add-spin"/>
          </div>
          <div class="wlsu-add-body">
            <div v-if="!addQuery" class="wlsu-add-hint">{{ $t('watchlist.typeToSearch') }}</div>
            <div v-else-if="addSearching && !addResults.length" class="wlsu-add-hint">{{ $t('common.searching') }}</div>
            <div v-else-if="addResults.length === 0 && addQuery" class="wlsu-add-hint">{{ $t('common.noResultsFor', { query: addQuery }) }}</div>
            <div v-else class="wlsu-add-results">
              <div v-for="item in addResults" :key="item.tmdb_id+'_'+item.media_type" class="wlsu-result-card">
                <div class="wlsu-result-poster">
                  <img v-if="item.poster" :src="item.poster" loading="lazy" @error="e=>e.target.style.display='none'"/>
                  <div v-else class="wlsu-result-poster-ph">{{ isMovie(item)?'🎬':'📺' }}</div>
                </div>
                <div class="wlsu-result-info">
                  <div class="wlsu-result-name">{{ item.name }}</div>
                  <div class="wlsu-result-meta">
                    <span class="wlsu-result-type">{{ typeLabel(item) }}</span>
                    <span v-if="item.year">{{ item.year }}</span>
                    <span v-if="item.vote_average" class="wlsu-result-rating">⭐ {{ item.vote_average?.toFixed(1) }}</span>
                  </div>
                  <p v-if="item.overview" class="wlsu-result-overview">{{ item.overview.slice(0,160) }}{{ item.overview.length>160?'…':'' }}</p>
                </div>
                <button
                  class="wlsu-eye-btn"
                  :class="{ tracked: isTracked(item.tmdb_id, item.media_type) }"
                  :title="isTracked(item.tmdb_id,item.media_type)?$t('watchlist.unfollow'):$t('watchlist.follow')"
                  @click.stop="toggleTrack(item)"
                >
                  <EyeOff v-if="!isTracked(item.tmdb_id, item.media_type)" :size="18" />
                  <Eye v-else :size="18" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWatchlist } from '@/composables/useWatchlist'
import WlMediaCard from './WlMediaCard.vue'
import { isMovie } from '@/constants/media'
import { Eye, EyeOff, LayoutGrid, List, Plus, Search, X } from 'lucide-vue-next'
const { t } = useI18n()
const { tracked, searchTMDB, toggleTrack, isTracked } = useWatchlist()

const viewMode = ref('wall')
const selected = ref(null)
const showAddModal = ref(false)
const addQuery = ref('')
const addResults = ref([])
const addSearching = ref(false)
const searchInput = ref(null)
let addTimer = null

function statusClass(item) {
  if (item.status==='ended') return 'status-ended'
  if (item.status==='hiatus') return 'status-hiatus'
  return 'status-active'
}

function typeLabel(item) {
  return isMovie(item) ? t('common.film') : t('common.series')
}

async function openAddModal() {
  showAddModal.value = true
  addQuery.value = ''
  addResults.value = []
  await nextTick()
  searchInput.value?.focus()
}

function closeAddModal() {
  showAddModal.value = false
  addQuery.value = ''
  addResults.value = []
}

function onAddSearch() {
  clearTimeout(addTimer)
  const q = addQuery.value.trim()
  if (q.length < 1) { addResults.value = []; return }
  addSearching.value = true
  addTimer = setTimeout(async () => {
    addResults.value = await searchTMDB(q)
    addSearching.value = false
  }, 300)
}
</script>

<style scoped>
.wlsu-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.wlsu-section-label { font-size:var(--text-2xs); text-transform:uppercase; letter-spacing:.8px; color:var(--text-muted); font-weight:var(--font-medium); }
.wlsu-empty { font-size:var(--text-base); color:var(--text-muted); text-align:center; padding:60px; }
.wlsu-view-toggle { display:flex; gap:4px; }
.vt-btn {
  width:34px; height:30px;
  border:1px solid var(--border-strong);
  background:rgba(255,255,255,0.03);
  border-radius:var(--radius-pill);
  cursor:pointer;
  color:rgba(255,255,255,.5);
  display:flex;align-items:center;justify-content:center;
  transition:all .18s;
  backdrop-filter:var(--blur-xs);
  -webkit-tap-highlight-color:transparent;
}
@media (hover:hover){
  .vt-btn:hover:not(.active){border-color:rgba(255,255,255,0.18);color:rgba(255,255,255,.85);transform:translateY(-1px)}
}
.vt-btn.active{
  background:var(--gradient-pill-active);
  border-color:var(--accent-500);
  color:#fff;
  box-shadow: var(--mk-pill-shadow-sm);
}

.wlsu-wall { display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:8px; }
.wlsu-card { position:relative; aspect-ratio:2/3; border-radius:var(--radius-btn); overflow:hidden; cursor:pointer; background:rgba(255,255,255,.03); border:.5px solid var(--border-default); transition:all var(--duration-base); }
.wlsu-card:hover { transform:translateY(-3px); border-color:rgba(99,102,241,.3); box-shadow:0 12px 32px rgba(0,0,0,.4); }
.wlsu-card:hover .wlsu-card-overlay { opacity:1; }
.wlsu-card-img { width:100%; height:100%; }
.wlsu-card-img img { width:100%; height:100%; object-fit:cover; display:block; }
.wlsu-card-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:28px; opacity:.15; background:rgba(255,255,255,.02); }
.wlsu-card-status { position:absolute; top:7px; right:7px; width:7px; height:7px; border-radius:50%; }
.status-active { background:#34d399; box-shadow:0 0 6px #34d399; }
.status-hiatus { background:var(--color-warning); box-shadow:0 0 6px var(--color-warning); }
.status-ended  { background:rgba(156,163,175,.5); }
.wlsu-card-overlay { position:absolute; inset:0; background:linear-gradient(to top,rgba(7,11,20,.97) 0%,rgba(7,11,20,.6) 50%,transparent 100%); opacity:0; transition:opacity var(--duration-base); display:flex; flex-direction:column; justify-content:flex-end; padding:10px; gap:4px; }
.wlsu-card-name { font-size:var(--text-2xs); font-weight:var(--font-bold); color:#fff; line-height:1.2; }
.wlsu-card-meta { font-size:.58rem; color:rgba(255,255,255,.45); }
.wlsu-untrack-btn { display:inline-flex; align-items:center; gap:4px; font-size:.58rem; padding:3px 7px; border-radius:5px; background:rgba(var(--color-error-rgb), .15); color:var(--color-error); border:none; cursor:pointer; font-family:inherit; margin-top:4px; transition:background var(--duration-fast); }
.wlsu-untrack-btn:hover { background:rgba(var(--color-error-rgb), .3); }
.wlsu-add-card { aspect-ratio:2/3; border-radius:var(--radius-btn); border:1px dashed rgba(255,255,255,.1); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; cursor:pointer; color:var(--text-muted); font-size:var(--text-2xs); transition:all var(--duration-fast); background:transparent; }
.wlsu-add-card:hover { border-color:rgba(99,102,241,.35); color:var(--accent-400); }
.wlsu-add-icon { opacity:.3; }
.wlsu-search-icon { color:var(--text-muted); flex-shrink:0; }

.wlsu-list-view { display:flex; flex-direction:column; gap:8px; }
.wlsu-add-list { display:flex; align-items:center; gap:8px; padding:10px 14px; border-radius:var(--radius-btn); border:.5px dashed rgba(255,255,255,.1); color:var(--text-muted); font-size:var(--text-sm); cursor:pointer; transition:all var(--duration-fast); }
.wlsu-add-list:hover { border-color:rgba(99,102,241,.35); color:var(--accent-400); }

.wlsu-detail-overlay { position:fixed; inset:0; z-index:9990; background:rgba(0,0,0,.6); backdrop-filter:blur(4px); display:flex; align-items:center; justify-content:center; padding:24px; }
.wlsu-detail { width:100%; max-width:520px; background:rgba(13,18,32,.98); border:.5px solid rgba(255,255,255,.1); border-radius:var(--radius-card); overflow:hidden; position:relative; box-shadow:var(--shadow-xl); }
.wlsu-detail-close { position:absolute; top:12px; right:12px; width:28px; height:28px; border-radius:var(--radius-sm); border:none; background:var(--surface-3); color:var(--text-muted); cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all var(--duration-fast); z-index:1; }
.wlsu-detail-close:hover { background:rgba(255,255,255,.1); color:#fff; }
.wlsu-detail-body { display:flex; gap:16px; padding:20px; }
.wlsu-detail-poster { width:100px; height:148px; border-radius:var(--radius-btn); overflow:hidden; flex-shrink:0; background:var(--surface-2); }
.wlsu-detail-poster img { width:100%; height:100%; object-fit:cover; }
.wlsu-detail-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:32px; opacity:.2; }
.wlsu-detail-info { flex:1; min-width:0; display:flex; flex-direction:column; gap:6px; padding-right:24px; }
.wlsu-detail-title { font-size:var(--text-md); font-weight:var(--font-bold); color:#fff; }
.wlsu-detail-meta { display:flex; gap:6px; flex-wrap:wrap; }
.wlsu-detail-meta span { font-size:var(--text-2xs); color:var(--text-muted); background:rgba(255,255,255,.05); padding:2px 7px; border-radius:5px; }
.wlsu-detail-overview { font-size:var(--text-xs); color:var(--text-secondary); line-height:var(--lh-relaxed); display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
.wlsu-tmdb-link { font-size:var(--text-2xs); color:var(--accent-400); text-decoration:none; }
.wlsu-untrack-btn-lg { display:inline-flex; align-items:center; gap:6px; padding:7px 14px; border-radius:var(--radius-btn); background:rgba(var(--color-error-rgb), .1); color:var(--color-error); border:.5px solid rgba(var(--color-error-rgb), .2); cursor:pointer; font-size:var(--text-xs); font-weight:var(--font-medium); font-family:inherit; margin-top:4px; transition:all var(--duration-fast); }
.wlsu-untrack-btn-lg:hover { background:rgba(var(--color-error-rgb), .25); }

.wlsu-add-overlay { position:fixed; inset:0; z-index:9995; background:rgba(0,0,0,.7); backdrop-filter:var(--blur-xs); display:flex; align-items:center; justify-content:center; padding:24px; }
.wlsu-add-modal { width:100%; max-width:680px; max-height:80vh; background:rgba(10,14,26,.98); border:.5px solid rgba(255,255,255,.1); border-radius:var(--radius-card); display:flex; flex-direction:column; overflow:hidden; box-shadow:0 32px 80px rgba(0,0,0,.6); animation:modal-in .18s ease-out; }
@keyframes modal-in { from{opacity:0;transform:scale(.97) translateY(8px)} to{opacity:1;transform:scale(1) translateY(0)} }
.wlsu-add-header { display:flex; align-items:center; justify-content:space-between; padding:16px 18px; border-bottom:.5px solid var(--border-default); flex-shrink:0; }
.wlsu-add-title { font-size:var(--text-base); font-weight:var(--font-bold); color:#fff; }
.wlsu-add-close { width:28px; height:28px; border-radius:var(--radius-sm); border:none; background:var(--surface-3); color:var(--text-muted); cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all var(--duration-fast); }
.wlsu-add-close:hover { background:rgba(255,255,255,.1); color:#fff; }
.wlsu-add-search-wrap { display:flex; align-items:center; gap:10px; padding:12px 18px; border-bottom:.5px solid var(--border-default); flex-shrink:0; }
.wlsu-add-input { flex:1; border:none; background:transparent; color:#fff; font-family:inherit; font-size:var(--text-base); outline:none; }
.wlsu-add-input::placeholder { color:var(--text-very-faint); }
.wlsu-add-spin { width:14px; height:14px; border:2px solid rgba(255,255,255,.1); border-top-color:var(--accent-500); border-radius:50%; animation:mk-spin .7s linear infinite; flex-shrink:0; }
.wlsu-add-body { flex:1; overflow-y:auto; padding:12px; }
.wlsu-add-hint { text-align:center; padding:40px; font-size:var(--text-sm); color:var(--text-very-faint); }
.wlsu-add-results { display:flex; flex-direction:column; gap:6px; }

.wlsu-result-card { display:flex; align-items:flex-start; gap:12px; padding:12px; border-radius:var(--radius-btn); background:rgba(255,255,255,.03); border:.5px solid var(--border-default); transition:border-color var(--duration-fast); position:relative; }
.wlsu-result-card:hover { border-color:rgba(99,102,241,.2); background:rgba(255,255,255,.05); }
.wlsu-result-poster { width:54px; height:80px; border-radius:var(--radius-sm); overflow:hidden; flex-shrink:0; background:var(--surface-2); }
.wlsu-result-poster img { width:100%; height:100%; object-fit:cover; }
.wlsu-result-poster-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:22px; opacity:.2; }
.wlsu-result-info { flex:1; min-width:0; padding-right:44px; }
.wlsu-result-name { font-size:var(--text-base); font-weight:var(--font-bold); color:#fff; margin-bottom:4px; }
.wlsu-result-meta { display:flex; gap:6px; align-items:center; margin-bottom:5px; flex-wrap:wrap; }
.wlsu-result-type { font-size:var(--text-3xs); font-weight:var(--font-medium); padding:2px 6px; border-radius:5px; background:rgba(99,102,241,.15); color: var(--accent-300); text-transform:uppercase; letter-spacing:.3px; }
.wlsu-result-meta span:not(.wlsu-result-type):not(.wlsu-result-rating) { font-size:var(--text-2xs); color:var(--text-muted); }
.wlsu-result-rating { font-size:var(--text-2xs); color:var(--color-warning); }
.wlsu-result-overview { font-size:var(--text-2xs); color:var(--text-faint); line-height:var(--lh-normal); display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

.wlsu-eye-btn {
  position:absolute; top:10px; right:10px;
  width:32px; height:32px; border-radius:50%; border:none; cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  transition:all var(--duration-fast); flex-shrink:0;
  background:rgba(var(--color-error-rgb), .12); color:var(--color-error);
}
.wlsu-eye-btn:hover { transform:scale(1.1); }
.wlsu-eye-btn.tracked { background:rgba(var(--color-success-rgb), .15); color:var(--color-success); }
.wlsu-eye-btn.tracked:hover { background:rgba(var(--color-success-rgb), .25); }
</style>
