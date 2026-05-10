<template>
  <div class="mm-center">
    <!-- Type -->
    <div class="mm-section">
      <div class="mm-label">{{ $t('mediaManager.contentType') }}</div>
      <div class="mm-type-row">
        <button
          class="mm-type-btn"
          :class="{ active: searchType === 'movie' }"
          @click="setType('movie')"
        >
          <Film />
          {{ $t('common.film') }}
        </button>
        <button class="mm-type-btn" :class="{ active: searchType === 'tv' }" @click="setType('tv')">
          <Monitor />
          {{ $t('common.series') }}
        </button>
      </div>
    </div>

    <!-- Recherche -->
    <div class="mm-section">
      <div class="mm-label">{{ $t('mediaManager.tmdbSearch') }}</div>
      <div class="mm-search-row">
        <input
          id="tmdb-q-vue"
          ref="tmdbQRef"
          name="tmdb-search"
          autocomplete="off"
          class="mm-search-in"
          :placeholder="$t('mediaManager.tmdbSearch')"
          @keydown.enter="runSearch"
        />
        <button class="mm-search-btn" @click="runSearch">
          <Search />
        </button>
      </div>
      <div class="mm-label mm-label--year">{{ $t('mediaManager.tmdbYearLabel') }}</div>
      <div class="mm-search-row">
        <input
          id="tmdb-y-vue"
          ref="tmdbYRef"
          v-model="tmdbYearQuery"
          name="tmdb-search-year"
          autocomplete="off"
          inputmode="numeric"
          maxlength="4"
          pattern="\d{4}"
          class="mm-search-in"
          :placeholder="$t('mediaManager.tmdbYearPh')"
          @keydown.enter="runSearch"
        />
      </div>
    </div>

    <!-- Seasons -->
    <div v-if="showSeasonPanel" class="mm-season-panel">
      <div class="mm-label">{{ $t('common.season', 1) }}</div>
      <div class="mm-season-row">
        <select v-model="currentSeason" class="mm-season-sel">
          <option :value="null">{{ $t('mediaManager.allSeasons') }}</option>
          <option v-for="s in seasons" :key="s.number" :value="s.number">
            {{ $t('mediaManager.seasonLabel', { n: s.number, eps: s.episodes }) }}
          </option>
        </select>
      </div>
      <div class="mm-season-row mm-row-spaced">
        <button class="mm-btn-sm mm-btn-sm--flex1" @click="doMatch(false)">
          <ArrowLeftRight />
          {{ $t('mediaManager.checkedFiles') }}
        </button>
        <button class="mm-btn-sm mm-btn-accent mm-btn-sm--flex1" @click="doMatch(true)">
          <Plus />
          {{ $t('mediaManager.addSeason') }}
        </button>
      </div>
    </div>

    <!-- Results TMDB -->
    <div class="mm-tmdb-list">
      <div v-if="!tmdbResults.length" class="mm-state">
        <Search :size="24" />
        <span>{{ $t('mediaManager.searchTitle') }}</span>
      </div>
      <div
        v-for="(item, i) in tmdbResults"
        :key="item.id"
        class="mm-tmdb-card"
        :class="{ selected: selectedTmdb?.id === item.id }"
        @click="pickTMDB(i)"
        @mouseenter="e => showTooltipTmdb(item, e)"
        @mousemove="moveTooltip"
        @mouseleave="hideTooltip"
        @dragover.prevent
        @drop.prevent="dropOnTmdb(i)"
      >
        <img v-if="item.poster" :src="item.poster" class="mm-tmdb-poster" loading="lazy" />
        <div v-else class="mm-tmdb-poster-ph">
          <Film :size="24" />
        </div>
        <div class="mm-tmdb-info">
          <div class="mm-tmdb-title">{{ item.title || item.name }}</div>
          <div class="mm-tmdb-meta">
            <span v-if="item.year" class="mm-badge">
              <Calendar :size="10" />
              {{ item.year }}
            </span>
            <span v-if="item.vote && item.vote > 0" class="mm-badge">
              ★ {{ item.vote.toFixed(1) }}
            </span>
            <span class="mm-badge">
              {{ item.type === 'tv' ? $t('common.series') : $t('common.film') }}
            </span>
            <span
              v-if="getGenreCategory(item.genre_ids)"
              class="mm-badge-genre"
              :style="{ background: getGenreCategory(item.genre_ids).color }"
            >
              {{ getGenreCategory(item.genre_ids).label }}
            </span>
          </div>
          <a
            v-if="item.tmdb_url"
            :href="item.tmdb_url"
            target="_blank"
            rel="noopener"
            class="mm-tmdb-link"
            @click.stop
          >
            {{ $t('mediaManager.viewOnTmdb') }}
          </a>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="mm-center-actions">
      <button class="mm-btn-full" :disabled="!canGenerate" @click="doMatch(false)">
        <ArrowLeftRight />
        {{ $t('mediaManager.generateNames') }}
      </button>
      <button class="mm-btn-full mm-btn-success" :disabled="!canRename" @click="startRename">
        <Check />
        {{ $t('mediaManager.renameAll') }}
      </button>
      <button class="mm-btn-full mm-btn-secondary" :disabled="!canFolders" @click="openFolderModal">
        <Folder />
        {{ $t('mediaManager.organizeFolders') }}
      </button>
      <button class="mm-btn-full mm-btn-config" @click="emit('openConfig', 'format')">
        <Settings :size="14" />
        {{ $t('mediaManager.configuration') }}
      </button>
      <button class="mm-btn-full mm-btn-emby" @click="refreshEmby">
        <RefreshCw :size="14" />
        {{ $t('mediaManager.scanEmby') }}
      </button>
      <div v-if="progress > 0" class="mm-progress">
        <div class="mm-progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- Tooltip TMDB -->
    <div
      class="mm-tooltip"
      :class="{ visible: tooltip.visible }"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="mm-tt-title">{{ tooltip.title }}</div>
      <div class="mm-tt-meta">{{ tooltip.year }} · ★ {{ tooltip.vote }}</div>
      <div class="mm-tt-overview">{{ tooltip.overview || $t('mediaManager.noSynopsis') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useMediaManager } from '@/composables/useMediaManager'
import {
  ArrowLeftRight,
  Calendar,
  Check,
  Film,
  Folder,
  Monitor,
  Plus,
  RefreshCw,
  Search,
  Settings,
} from 'lucide-vue-next'

const emit = defineEmits(['openConfig'])

const {
  searchType,
  tmdbResults,
  tmdbYearQuery,
  selectedTmdb,
  currentSeason,
  seasons,
  showSeasonPanel,
  tooltip,
  progress,
  canGenerate,
  canRename,
  canFolders,
  setType,
  doSearch,
  pickTMDB,
  showTooltipTmdb,
  moveTooltip,
  hideTooltip,
  doMatch,
  dropOnTmdb,
  startRename,
  openFolderModal,
  refreshEmby,
  getGenreCategory,
} = useMediaManager()

const tmdbQRef = ref(null)
const tmdbYRef = ref(null)

function parseYearInputOrNull(raw) {
  const s = String(raw ?? '').trim()
  if (!/^\d{4}$/.test(s)) return null
  const n = parseInt(s, 10)
  return n >= 1900 && n <= 2099 ? n : null
}

function runSearch() {
  doSearch(false, tmdbQRef.value?.value || '', parseYearInputOrNull(tmdbYRef.value?.value))
}

defineExpose({ tmdbQRef, tmdbYRef })
</script>

<style scoped>
.mm-label--year {
  margin-top: 0.5rem;
}
</style>
