<template>
  <div>
    <div class="pt-admin-toolbar">
      <input
        v-model="searchQuery"
        class="pt-input"
        :placeholder="$t('portal.admin.searchTmdb')"
        @keyup.enter="searchTmdb"
      />
      <button class="pt-btn pt-btn--primary" :disabled="!searchQuery.trim()" @click="searchTmdb">
        {{ $t('common.search') }}
      </button>
    </div>

    <!-- Search results -->
    <div v-if="searchResults.length" class="pt-featured-results">
      <div v-for="item in searchResults" :key="item.id" class="pt-featured-result">
        <img v-if="item.poster" :src="item.poster" class="pt-featured-thumb" />
        <div class="pt-featured-result-info">
          <span class="pt-featured-result-title">{{ item.title }}</span>
          <span class="pt-featured-result-meta">{{ item.year }} · {{ item.media_type }}</span>
        </div>
        <button class="pt-btn pt-btn--primary" @click="addFeatured(item)">
          {{ $t('portal.admin.addToHero') }}
        </button>
      </div>
    </div>

    <!-- Current featured list -->
    <h4 class="pt-section-subtitle">{{ $t('portal.admin.currentFeatured') }}</h4>
    <p class="pt-section-desc">
      {{ $t('portal.admin.featured.desc') }}
    </p>
    <div class="pt-admin-table">
      <div v-for="f in featured" :key="f.id" class="pt-admin-row">
        <span class="pt-featured-order">#{{ f.sort_order }}</span>
        <span class="pt-featured-name">{{ f.title }}</span>
        <span class="pt-featured-type">{{ f.media_type }}</span>
        <label class="pt-toggle-label">
          <input
            type="checkbox"
            :checked="f.active"
            @change="toggleActive(f.id, $event.target.checked)"
          />
          {{ f.active ? $t('common.active') : $t('common.inactive') }}
        </label>
        <button class="pt-icon-btn" @click="remove(f.id)">
          <Trash2 :size="16" />
        </button>
      </div>
      <div v-if="!featured.length" class="pt-empty">{{ $t('portal.admin.noFeatured') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { Trash2 } from 'lucide-vue-next'

const { apiGet, apiPost, apiPut, apiDelete } = useApi()
const { showToast } = useToast()
const { t } = useI18n()

const featured = ref([])
const searchQuery = ref('')
const searchResults = ref([])

async function loadFeatured() {
  const res = await apiGet('/api/portal/featured/all').catch(() => null)
  if (res) featured.value = res.items
}

async function searchTmdb() {
  if (!searchQuery.value.trim()) return
  const res = await apiGet(
    `/api/portal/catalog/search?q=${encodeURIComponent(searchQuery.value)}`,
  ).catch(() => null)
  if (res) searchResults.value = res.items
}

async function addFeatured(item) {
  await apiPost('/api/portal/featured', {
    tmdb_id: item.tmdb_id || item.id,
    media_type: item.media_type || 'movie',
    title: item.title,
    overview: item.overview || '',
    poster_url: item.poster_url || item.poster || '',
    backdrop: item.backdrop || '',
    vote: item.vote || 0,
    year: item.year || '',
    sort_order: featured.value.length,
  })
  searchResults.value = []
  searchQuery.value = ''
  showToast(t('common.saved'), TOAST_TYPE.OK)
  await loadFeatured()
}

async function toggleActive(id, active) {
  await apiPut(`/api/portal/featured/${id}`, { active })
  await loadFeatured()
}

async function remove(id) {
  await apiDelete(`/api/portal/featured/${id}`)
  showToast(t('common.success'), TOAST_TYPE.OK)
  await loadFeatured()
}

onMounted(loadFeatured)
</script>

<style scoped>
.pt-admin-toolbar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.pt-input {
  flex: 1;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--text-sm);
}
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--font-medium);
  cursor: pointer;
  font-size: var(--text-sm);
}
.pt-btn--primary {
  background: var(--accent);
  color: var(--text-primary);
}
.pt-featured-results {
  margin-bottom: 1.5rem;
}
.pt-featured-result {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-featured-thumb {
  width: 40px;
  height: 60px;
  border-radius: 3px;
  object-fit: cover;
}
.pt-featured-result-info {
  flex: 1;
}
.pt-featured-result-title {
  display: block;
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-size: var(--text-base);
}
.pt-featured-result-meta {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.pt-section-subtitle {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 1rem 0 0.5rem;
}
.pt-section-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0.25rem 0 1rem;
}
.pt-admin-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-featured-order {
  font-weight: var(--font-bold);
  color: var(--text-muted);
  width: 2rem;
  font-size: var(--text-sm);
}
.pt-featured-name {
  flex: 1;
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-size: var(--text-base);
}
.pt-featured-type {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
}
.pt-toggle-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
}
.pt-icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.pt-icon-btn:hover {
  color: var(--color-error);
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 1.5rem 0;
}
</style>
