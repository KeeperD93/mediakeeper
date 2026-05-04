<template>
  <div class="sub-panel sub-panel--search">
    <!-- Mode toggle -->
    <div class="ss-mode-toggle">
      <button
        class="ss-mode-btn"
        :class="{ active: searchMode === 'subtitles' }"
        @click="searchMode = 'subtitles'"
      >
        <Search :size="14" />
        {{ $t('subtitles.searchSubs') }}
      </button>
      <button
        class="ss-mode-btn"
        :class="{ active: searchMode === 'streams' }"
        @click="searchMode = 'streams'"
      >
        <Calendar :size="14" />
        {{ $t('subtitles.searchStreams') }}
      </button>
    </div>

    <!-- ═══ MODE: Recherche sous-titres OpenSubtitles ═══ -->
    <template v-if="searchMode === 'subtitles'">
      <div class="ss-card sub-search-card">
        <div class="sub-search-row">
          <input
            v-model="searchQuery"
            class="sub-search-input"
            :placeholder="$t('subtitles.searchPlaceholder')"
            @keydown.enter="doTmdbSearch"
          />
          <select v-model="searchType" class="sub-filter-sel">
            <option value="movie">{{ $t('subtitles.typeMovie') }}</option>
            <option value="tv">{{ $t('subtitles.typeSeries') }}</option>
          </select>
          <select v-model="searchLangs" class="sub-filter-sel">
            <option :value="defaultLanguagesParam">
              {{ defaultLanguages.map(l => langShort(l)).join(' + ') }}
            </option>
            <option
              v-for="lang in defaultLanguages"
              :key="lang"
              :value="langShort(lang).toLowerCase()"
            >
              {{ langShort(lang) }}
            </option>
            <option value="">{{ $t('subtitles.typeAll') }}</option>
          </select>
          <button
            class="sub-search-go"
            :disabled="searching || !searchQuery.trim()"
            @click="doTmdbSearch"
          >
            <Search v-if="!searching" :size="16" />
            <span v-else class="mk-spin mk-spin-16" />
          </button>
        </div>
        <div
          v-if="!tmdbResults.length && !searchResults.length && !searching"
          class="sub-search-hint"
        >
          {{ $t('subtitles.searchHint') }}
        </div>
      </div>

      <!-- TMDB results -->
      <div v-if="tmdbResults.length && !selectedTmdb" class="ss-card sub-tmdb-card">
        <div class="sub-section-title">{{ $t('subtitles.tmdbSelectMedia') }}</div>
        <div v-for="m in tmdbResults" :key="m.id" class="sub-tmdb-row" @click="selectTmdb(m)">
          <img v-if="m.poster" :src="m.poster" class="sub-tmdb-poster" alt="" />
          <div v-else class="sub-tmdb-poster sub-tmdb-poster-empty">
            <Film :size="16" :stroke-width="1.5" />
          </div>
          <div class="sub-tmdb-info">
            <span class="sub-tmdb-name">{{ m.title }}</span>
            <span class="sub-tmdb-meta">
              <span v-if="m.year">{{ m.year }}</span>
              <span v-if="m.vote" class="sub-tmdb-vote">{{ m.vote }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Selected banner -->
      <div v-if="selectedTmdb" class="ss-card sub-selected-banner">
        <img
          v-if="selectedTmdb.poster"
          :src="selectedTmdb.poster"
          class="sub-selected-poster"
          alt=""
        />
        <div class="sub-selected-info">
          <span class="sub-selected-name">{{ selectedTmdb.title }}</span>
          <span class="sub-selected-year">{{ selectedTmdb.year }}</span>
        </div>
        <button class="sub-selected-clear" @click="clearTmdbSelection">
          <X :size="14" />
        </button>
      </div>

      <!-- OpenSubtitles results -->
      <div v-if="searchResults.length" class="ss-card sub-os-card">
        <div class="sub-section-title">
          {{ searchResults.length }} {{ $t('subtitles.results') }}
        </div>
        <div class="sub-os-results">
          <SubOsResultRow
            v-for="r in searchResults"
            :key="r.file_id"
            :result="r"
            :downloading="downloading === r.file_id"
            @download="downloadSearchResult($event)"
          />
        </div>
      </div>

      <SubDownloadModal
        :visible="!!downloadModal"
        :default-path="downloadDest"
        @close="downloadModal = null"
        @confirm="confirmDownload"
      />
    </template>

    <!-- ═══ MODE: Recherche pistes in la library ═══ -->
    <template v-else>
      <div class="ss-card sub-search-card">
        <div class="sub-search-row">
          <input
            v-model="streamQuery"
            class="sub-search-input"
            :placeholder="$t('subtitles.streamSearchPlaceholder')"
            @keydown.enter="doStreamSearch"
          />
          <select v-model="streamTypeFilter" class="sub-filter-sel">
            <option value="all">{{ $t('subtitles.typeAll') }}</option>
            <option value="audio">Audio</option>
            <option value="subtitle">{{ $t('subtitles.existingSubs') }}</option>
          </select>
          <button
            class="sub-search-go"
            :disabled="streamSearching || !streamQuery.trim()"
            @click="doStreamSearch"
          >
            <Search v-if="!streamSearching" :size="16" />
            <span v-else class="mk-spin mk-spin-16" />
          </button>
        </div>
        <div class="sub-search-hint">{{ $t('subtitles.streamSearchHint') }}</div>
      </div>

      <!-- Stream results -->
      <div v-if="streamResults.length" class="ss-stream-results">
        <!-- Batch actions -->
        <div class="ss-batch-bar">
          <label class="ss-select-all">
            <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
            {{ $t('subtitles.selectAll') }} ({{ selectedStreams.length }})
          </label>
          <button
            v-if="selectedStreams.length"
            class="ss-batch-del"
            :disabled="batchRemoving"
            @click="batchRemove"
          >
            <Trash2 :size="13" />
            {{ $t('subtitles.deleteSelected') }} ({{ selectedStreams.length }})
          </button>
          <span class="ss-batch-total">{{ streamTotal }} {{ $t('subtitles.results') }}</span>
        </div>

        <!-- Items with matching streams -->
        <div v-for="item in streamResults" :key="item.item_id" class="ss-stream-item ss-card">
          <div class="ss-stream-header">
            <img
              :src="'/api/emby/image/' + (item.poster_id || item.item_id)"
              class="ss-stream-poster"
              alt=""
              loading="lazy"
              @error="$event.target.style.display = 'none'"
            />
            <div class="ss-stream-info">
              <span class="ss-stream-name">
                {{ item.series_name ? item.series_name + ' — ' : '' }}{{ item.name }}
              </span>
              <span class="ss-stream-meta">
                <span class="ss-stream-tag" :class="item.type === 'Movie' ? 'tag-movie' : 'tag-ep'">
                  {{
                    item.type === 'Movie'
                      ? $t('subtitles.typeMovie')
                      : `S${item.season || 0}E${item.episode || 0}`
                  }}
                </span>
                <span v-if="item.year" class="ss-stream-year">{{ item.year }}</span>
              </span>
            </div>
          </div>
          <div class="ss-stream-list">
            <div v-for="s in item.matching_streams" :key="s.index" class="ss-stream-row">
              <input
                type="checkbox"
                class="ss-stream-check"
                :checked="isStreamSelected(item.item_id, s.index)"
                @change="toggleStreamSelect(item.item_id, s.index, item, s)"
              />
              <span
                class="ss-stream-type-badge"
                :class="s.type === STREAM_TYPE.AUDIO ? 'badge-audio' : 'badge-sub'"
              >
                {{ s.type === STREAM_TYPE.AUDIO ? 'AUD' : 'SUB' }}
              </span>
              <span class="ss-stream-lang">{{ s.language.toUpperCase() }}</span>
              <span class="ss-stream-title">{{ s.title }}</span>
              <span class="ss-stream-codec">{{ s.codec }}</span>
              <span v-if="s.channels" class="ss-stream-channels">
                {{ formatChannels(s.channels) }}
              </span>
              <span v-if="s.is_default" class="ss-badge badge-default">Default</span>
              <span v-if="s.is_forced" class="ss-badge badge-forced">Forced</span>
              <button
                class="ss-del-btn"
                :title="$t('subtitles.removeStream')"
                @click="removeSingleStream(item.item_id, s.index, s)"
              >
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="streamTotal > streamResults.length" class="ss-more">
          <button class="ss-more-btn" :disabled="streamSearching" @click="loadMoreStreams">
            {{ $t('subtitles.loadMore') }}
          </button>
        </div>
      </div>

      <!-- Empty -->
      <MkEmptyState
        v-if="!streamSearching && streamSearched && !streamResults.length"
        :title="$t('common.noResults')"
      />
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { STREAM_TYPE } from '@/constants/subtitles'
import { useSubtitles } from '@/composables/useSubtitles'
import SubOsResultRow from './SubOsResultRow.vue'
import SubDownloadModal from './SubDownloadModal.vue'
import { useSubStreamSearch } from '@/composables/useSubStreamSearch'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import { Calendar, Film, Search, Trash2, X } from 'lucide-vue-next'

import '@/assets/styles/subtitles/search-tab.css'

const props = defineProps({
  initialQuery: { type: String, default: '' },
})

const { t } = useI18n()
const { apiGet, apiPost } = useApi()
const { showToast } = useToast()
const { loadQuota, defaultLanguages, defaultLanguagesParam, translateError } = useSubtitles()

const searchMode = ref('subtitles')

// ── Subtitle search state ──────────────────────────────────────────────────
const searchQuery = ref(props.initialQuery)
const searchType = ref('movie')
const LANG_SHORT = {
  fre: 'FR',
  eng: 'EN',
  spa: 'ES',
  ger: 'DE',
  ita: 'IT',
  por: 'PT',
  jpn: 'JP',
  chi: 'ZH',
  kor: 'KO',
  rus: 'RU',
  ara: 'AR',
  hin: 'HI',
  nld: 'NL',
  dut: 'NL',
  pol: 'PL',
  tur: 'TR',
  swe: 'SV',
  dan: 'DA',
  nor: 'NO',
  fin: 'FI',
  ces: 'CZ',
  cze: 'CZ',
  ron: 'RO',
  rum: 'RO',
  hun: 'HU',
  ell: 'EL',
  gre: 'EL',
  heb: 'HE',
  tha: 'TH',
  vie: 'VI',
  ind: 'ID',
  ukr: 'UK',
}
function langShort(code) {
  return LANG_SHORT[code] || code.slice(0, 2).toUpperCase()
}
const searchLangs = ref(defaultLanguagesParam.value)
const searchResults = ref([])
const tmdbResults = ref([])
const selectedTmdb = ref(null)
const searching = ref(false)
const downloading = ref(null)
const downloadModal = ref(null)
const downloadDest = ref('')

// ── Stream search (library) — logic extracted to dedicated composable ──────
const {
  streamQuery,
  streamTypeFilter,
  streamResults,
  streamTotal,
  streamSearching,
  streamSearched,
  selectedStreams,
  batchRemoving,
  allSelected,
  doStreamSearch,
  loadMoreStreams,
  isStreamSelected,
  toggleStreamSelect,
  toggleSelectAll,
  removeSingleStream,
  batchRemove,
} = useSubStreamSearch()

// ── Subtitle search functions ──────────────────────────────────────────────
async function doTmdbSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  tmdbResults.value = []
  searchResults.value = []
  selectedTmdb.value = null
  try {
    const endpoint =
      searchType.value === 'tv' ? '/api/media/tmdb/search/tv' : '/api/media/tmdb/search/movie'
    const d = await apiGet(`${endpoint}?q=${encodeURIComponent(searchQuery.value.trim())}`)
    if (d && Array.isArray(d) && d.length > 0) tmdbResults.value = d
    else await doDirectSearch(searchQuery.value.trim())
  } catch {
    await doDirectSearch(searchQuery.value.trim())
  }
  searching.value = false
}

async function selectTmdb(media) {
  selectedTmdb.value = media
  tmdbResults.value = []
  searching.value = true
  searchResults.value = []
  try {
    const d = await apiPost('/api/subtitles/search', {
      query: media.title,
      tmdb_id: String(media.id),
      languages: searchLangs.value,
    })
    if (d && d.results) searchResults.value = d.results
    if (!searchResults.value.length) showToast(t('common.noResults'), TOAST_TYPE.INFO)
  } catch {
    showToast(t('common.error'), TOAST_TYPE.ERR)
  }
  searching.value = false
}

async function doDirectSearch(query) {
  try {
    const d = await apiPost('/api/subtitles/search', { query, languages: searchLangs.value })
    if (d && d.results) searchResults.value = d.results
    if (!searchResults.value.length) showToast(t('common.noResults'), TOAST_TYPE.INFO)
  } catch (e) {
    console.error('[SubSearchTab.doDirectSearch] search failed', e)
    showToast(t('common.error'), TOAST_TYPE.ERR)
  }
}

function clearTmdbSelection() {
  selectedTmdb.value = null
  searchResults.value = []
  tmdbResults.value = []
}

function downloadSearchResult(r) {
  downloadModal.value = r
  downloadDest.value = r.file_name || `subtitle.${r.language || 'und'}.srt`
}

async function confirmDownload(dest) {
  if (!downloadModal.value) return
  const r = downloadModal.value
  downloading.value = r.file_id
  downloadModal.value = null
  try {
    const d = await apiPost('/api/subtitles/download', {
      file_id: r.file_id,
      destination: dest,
      media_name: r.feature_title || '',
      language: r.language || '',
      subtitle_id: r.subtitle_id || '',
      file_name: r.file_name || '',
      quality_score: r.quality_score || 0,
      hash_match: r.hash_match || false,
      hearing_impaired: r.hearing_impaired || false,
      foreign_parts_only: r.foreign_parts_only || false,
      from_trusted: r.from_trusted || false,
      ai_translated: r.ai_translated || false,
    })
    if (d && d.success) {
      showToast(t('subtitles.downloaded'), TOAST_TYPE.OK)
      loadQuota()
    } else if (d && d.error) showToast(translateError(d.error), TOAST_TYPE.ERR)
  } catch {
    showToast(t('common.error'), TOAST_TYPE.ERR)
  }
  downloading.value = null
}

function formatChannels(ch) {
  if (ch === 1) return 'Mono'
  if (ch === 2) return 'Stereo'
  if (ch === 6) return '5.1'
  if (ch === 8) return '7.1'
  return `${ch}ch`
}

if (props.initialQuery) doTmdbSearch()

defineExpose({ doTmdbSearch, searchQuery })
</script>
