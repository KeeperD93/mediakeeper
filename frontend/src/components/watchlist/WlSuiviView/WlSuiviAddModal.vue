<template>
  <Teleport to="body">
    <div v-if="open" class="wlsu-add-overlay" @click.self="$emit('close')">
      <div class="wlsu-add-modal">
        <div class="wlsu-add-header">
          <span class="wlsu-add-title">{{ $t('watchlist.addContent') }}</span>
          <button class="wlsu-add-close" @click="$emit('close')">
            <X :size="14" />
          </button>
        </div>
        <div class="wlsu-add-search-wrap">
          <Search :size="15" class="wlsu-search-icon" />
          <input
            ref="searchInput"
            v-model="addQuery"
            type="text"
            :placeholder="$t('watchlist.searchMovieOrSeries')"
            class="wlsu-add-input"
            @input="onAddSearch"
          />
          <div v-if="addSearching" class="wlsu-add-spin" />
        </div>
        <div class="wlsu-add-body">
          <div v-if="!addQuery" class="wlsu-add-hint">{{ $t('watchlist.typeToSearch') }}</div>
          <div v-else-if="addSearching && !addResults.length" class="wlsu-add-hint">
            {{ $t('common.searching') }}
          </div>
          <div v-else-if="addResults.length === 0 && addQuery" class="wlsu-add-hint">
            {{ $t('common.noResultsFor', { query: addQuery }) }}
          </div>
          <div v-else class="wlsu-add-results">
            <WlSuiviResultCard
              v-for="item in addResults"
              :key="item.tmdb_id + '_' + item.media_type"
              :item="item"
              :tracked="isTracked(item.tmdb_id, item.media_type)"
              @toggle-track="$emit('toggle-track', $event)"
            />
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import WlSuiviResultCard from './WlSuiviResultCard.vue'
import { Search, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, required: true },
  isTracked: { type: Function, required: true },
  searchTmdb: { type: Function, required: true },
})
defineEmits(['close', 'toggle-track'])

const addQuery = ref('')
const addResults = ref([])
const addSearching = ref(false)
const searchInput = ref(null)
let addTimer = null

watch(
  () => props.open,
  async v => {
    if (v) {
      addQuery.value = ''
      addResults.value = []
      await nextTick()
      searchInput.value?.focus()
    } else {
      addQuery.value = ''
      addResults.value = []
    }
  },
)

function onAddSearch() {
  clearTimeout(addTimer)
  const q = addQuery.value.trim()
  if (q.length < 1) {
    addResults.value = []
    return
  }
  addSearching.value = true
  addTimer = setTimeout(async () => {
    addResults.value = await props.searchTmdb(q)
    addSearching.value = false
  }, 300)
}
</script>

<style scoped>
.wlsu-search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.wlsu-add-overlay {
  position: fixed;
  inset: 0;
  z-index: 9995;
  background: rgb(0, 0, 0, 0.7);
  backdrop-filter: var(--blur-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.wlsu-add-modal {
  width: 100%;
  max-width: 680px;
  max-height: 80vh;
  background: rgb(10, 14, 26, 0.98);
  border: 0.5px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 32px 80px rgb(0, 0, 0, 0.6);
  animation: modal-in 0.18s ease-out;
}
@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.wlsu-add-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 0.5px solid var(--border-default);
  flex-shrink: 0;
}
.wlsu-add-title {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: #fff;
}
.wlsu-add-close {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--surface-3);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}
.wlsu-add-close:hover {
  background: rgb(255, 255, 255, 0.1);
  color: #fff;
}
.wlsu-add-search-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-bottom: 0.5px solid var(--border-default);
  flex-shrink: 0;
}
.wlsu-add-input {
  flex: 1;
  border: none;
  background: transparent;
  color: #fff;
  font-family: inherit;
  font-size: var(--text-base);
  outline: none;
}
.wlsu-add-input::placeholder {
  color: var(--text-very-faint);
}
.wlsu-add-spin {
  width: 14px;
  height: 14px;
  border: 2px solid rgb(255, 255, 255, 0.1);
  border-top-color: var(--accent-500);
  border-radius: 50%;
  animation: mk-spin 0.7s linear infinite;
  flex-shrink: 0;
}
.wlsu-add-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.wlsu-add-hint {
  text-align: center;
  padding: 40px;
  font-size: var(--text-sm);
  color: var(--text-very-faint);
}
.wlsu-add-results {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
