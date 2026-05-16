<template>
  <div class="sub-panel">
    <!-- Filters -->
    <div class="sub-hist-filters glass-card">
      <input
        v-model="searchText"
        class="sub-filter-input"
        :placeholder="$t('subtitles.searchLibrary')"
        @input="debounceLoad"
      />
      <select v-model="filterLang" class="sub-filter-sel mk-select-chevron" @change="reload">
        <option value="">{{ $t('subtitles.typeAll') }}</option>
        <option value="fr">FR</option>
        <option value="en">EN</option>
        <option value="es">ES</option>
        <option value="de">DE</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="loading && !history.length" class="sub-center">
      <span class="mk-spin mk-spin-24" />
    </div>

    <!-- History list -->
    <div v-else-if="history.length" class="sub-hist-list">
      <div v-for="dl in filteredHistory" :key="dl.id" class="sub-hist-row glass-card">
        <div class="sub-hist-main">
          <span class="sub-hist-name">{{ dl.media_name }}</span>
          <span class="sub-hist-meta">
            <span class="sub-hist-lang" :class="'lang-' + dl.language">
              {{ dl.language.toUpperCase() }}
            </span>
            <SubQualityStars v-if="dl.quality_score" :score="dl.quality_score" />
            <span v-if="dl.from_trusted" class="sub-tag tag-trusted">
              {{ $t('subtitles.trusted') }}
            </span>
            <span v-if="dl.hash_match" class="sub-tag tag-hash">HASH</span>
            <span v-if="dl.hearing_impaired" class="sub-tag tag-hi">HI</span>
            <span v-if="dl.ai_translated" class="sub-tag tag-ai">AI</span>
          </span>
        </div>
        <div class="sub-hist-right">
          <span class="sub-hist-file">{{ dl.file_name }}</span>
          <span class="sub-hist-date">{{ formatDate(dl.downloaded_at) }}</span>
          <span v-if="dl.source" class="sub-hist-source">{{ dl.source }}</span>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="historyTotal > history.length" class="sub-hist-more">
        <button class="sub-hist-more-btn" :disabled="loading" @click="loadMore">
          {{ $t('subtitles.loadMore') }}
        </button>
      </div>
    </div>

    <!-- Empty -->
    <MkEmptyState v-else :icon="Clock" :title="$t('subtitles.noHistory')" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSubtitles } from '@/composables/useSubtitles'
import SubQualityStars from './SubQualityStars.vue'
import { Clock } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

const { history, historyTotal, loadHistory } = useSubtitles()

const loading = ref(false)
const searchText = ref('')
const filterLang = ref('')
let _offset = 0
let _debounceTimer = null

const filteredHistory = computed(() => {
  if (!searchText.value.trim()) return history.value
  const q = searchText.value.toLowerCase()
  return history.value.filter(
    d => d.media_name.toLowerCase().includes(q) || (d.file_name || '').toLowerCase().includes(q),
  )
})

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return (
    d.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' +
    d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  )
}

async function reload() {
  loading.value = true
  _offset = 0
  await loadHistory({ limit: 50, offset: 0, language: filterLang.value })
  loading.value = false
}

async function loadMore() {
  loading.value = true
  _offset += 50
  await loadHistory({ limit: 50, offset: _offset, language: filterLang.value })
  loading.value = false
}

function debounceLoad() {
  clearTimeout(_debounceTimer)
  _debounceTimer = setTimeout(reload, 400)
}

onMounted(reload)
</script>

<style scoped>
.sub-hist-filters {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.sub-filter-input {
  flex: 1;
  min-width: 160px;
  height: 36px;
  padding: 0 12px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}
.sub-filter-input:focus {
  border-color: rgb(var(--accent-rgb), 0.4);
}
.sub-filter-sel {
  height: 36px;
  padding: 0 30px 0 12px;
  border-radius: var(--radius-btn);
  font-size: var(--text-2xs);
  background-color: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  cursor: pointer;
  box-sizing: border-box;
}
.sub-filter-sel option {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.sub-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  gap: 12px;
}

.sub-hist-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sub-hist-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
}
.sub-hist-main {
  flex: 1;
  min-width: 0;
}
.sub-hist-name {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub-hist-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 3px;
}
.sub-hist-lang {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  padding: 2px 6px;
  border-radius: 4px;
}
.lang-fr {
  background: rgb(59, 130, 246, 0.12);
  color: var(--color-info);
}
.lang-en {
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}

.sub-tag {
  font-size: 0.54rem;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: var(--font-medium);
}
.tag-trusted {
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}
.tag-hash {
  background: rgb(52, 211, 153, 0.12);
  color: #34d399;
}
.tag-hi {
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
}
.tag-ai {
  background: rgb(var(--color-info-rgb), 0.12);
  color: var(--color-info);
}

.sub-hist-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.sub-hist-file {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub-hist-date {
  font-size: 0.58rem;
  color: var(--text-muted);
}
.sub-hist-source {
  font-size: 0.52rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.sub-hist-more {
  display: flex;
  justify-content: center;
  padding: 16px;
}
.sub-hist-more-btn {
  padding: 8px 24px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
}
.sub-hist-more-btn:hover {
  background: rgb(255, 255, 255, 0.08);
}
.sub-hist-more-btn:disabled {
  opacity: 0.4;
}

.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}

@media (max-width: 767px) {
  .sub-filter-input,
  .sub-filter-sel {
    min-height: 44px;
  }
}
</style>
