<template>
  <div class="wls-toolbar">
    <div class="wls-search-wrap">
      <Search class="wls-search-icon" :size="14" />
      <input
        :value="searchQuery"
        class="wls-search"
        type="text"
        :placeholder="$t('watchlist.searchSeries')"
        @input="$emit('update:searchQuery', $event.target.value)"
      />
      <button
        v-if="searchQuery"
        class="wls-search-clear"
        @click="$emit('update:searchQuery', '')"
      >
        <X :size="12" />
      </button>
    </div>

    <div class="wls-filters">
      <select
        :value="sortBy"
        class="wls-select mk-select-chevron"
        @change="$emit('update:sortBy', $event.target.value)"
      >
        <option value="missing">{{ $t('watchlist.sortMissing') }}</option>
        <option value="name">{{ $t('watchlist.sortName') }}</option>
        <option value="progress">{{ $t('watchlist.sortCompletion') }}</option>
        <option value="year">{{ $t('watchlist.sortYear') }}</option>
      </select>

      <select
        :value="groupBy"
        class="wls-select mk-select-chevron"
        @change="$emit('update:groupBy', $event.target.value)"
      >
        <option value="none">{{ $t('watchlist.groupNone') }}</option>
        <option value="status">{{ $t('watchlist.groupStatus') }}</option>
        <option value="year">{{ $t('watchlist.groupYear') }}</option>
      </select>

      <div class="wls-export-group">
        <button
          class="wls-export-btn"
          :title="$t('watchlist.exportCsv')"
          @click="$emit('export-csv')"
        >
          <Download :size="15" />
          CSV
        </button>
        <button
          class="wls-export-btn"
          :title="$t('watchlist.exportJson')"
          @click="$emit('export-json')"
        >
          <Download :size="15" />
          JSON
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Download, Search, X } from 'lucide-vue-next'

defineProps({
  searchQuery: { type: String, required: true },
  sortBy: { type: String, required: true },
  groupBy: { type: String, required: true },
})
defineEmits(['update:searchQuery', 'update:sortBy', 'update:groupBy', 'export-csv', 'export-json'])
</script>

<style scoped>
.wls-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
}
.wls-search-wrap {
  position: relative;
  flex: 1;
  min-width: 180px;
}
.wls-search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}
.wls-search {
  width: 100%;
  padding: 7px 30px 7px 32px;
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border-strong);
  background: rgb(255, 255, 255, 0.03);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
  transition: border-color var(--duration-fast);
}
.wls-search:focus {
  border-color: rgb(var(--accent-rgb), 0.4);
}
.wls-search::placeholder {
  color: var(--text-muted);
}
.wls-search-clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-2xs);
  padding: 2px 4px;
}
.wls-filters {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.wls-select {
  height: 36px;
  padding: 0 30px 0 10px;
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border-strong);
  background-color: rgb(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  font-family: inherit;
  cursor: pointer;
  outline: none;
  box-sizing: border-box;
}
.wls-select:focus {
  border-color: rgb(var(--accent-rgb), 0.4);
}
.wls-select option {
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.wls-export-group {
  display: flex;
  gap: 4px;
}
.wls-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border-strong);
  background: rgb(255, 255, 255, 0.03);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--duration-fast);
}
.wls-export-btn:hover {
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-400);
  border-color: rgb(var(--accent-rgb), 0.25);
}

@media (max-width: 1024px) {
  .wls-toolbar {
    flex-direction: column;
  }
  .wls-search-wrap {
    min-width: 100%;
  }
}

@media (max-width: 767px) {
  .wls-search,
  .wls-select,
  .wls-export-btn {
    min-height: 44px;
  }
}
</style>
