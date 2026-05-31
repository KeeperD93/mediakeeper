<template>
  <div class="sf-bar">
    <!-- Group 1 — content filters (what data is shown) -->
    <div class="sf-group sf-group--filters">
      <div class="sf-search-wrap">
        <span class="sf-search-icon">&#8981;</span>
        <input
          :value="libSearch"
          class="sf-search"
          :placeholder="$t('subtitles.searchLibrary')"
          @input="onSearch"
        />
      </div>
      <select :value="libType" class="sf-select mk-select-chevron" @change="onType">
        <option value="Movie,Episode">{{ $t('subtitles.typeAll') }}</option>
        <option value="Movie">{{ $t('subtitles.typeMovie') }}</option>
        <option value="Episode">{{ $t('subtitles.typeSeries') }}</option>
      </select>
      <select :value="libLibrary" class="sf-select mk-select-chevron" @change="onLibrary">
        <option value="">{{ $t('subtitles.allLibraries') }}</option>
        <option v-for="lib in embyLibraries" :key="lib.id" :value="lib.id">{{ lib.name }}</option>
      </select>
    </div>

    <div class="sf-divider" aria-hidden="true"></div>

    <!-- Group 2 — subtitle status filter -->
    <div class="sf-group sf-group--status sf-status-btns">
      <button class="sf-status-btn" :class="{ active: libStatus === '' }" @click="onStatus('')">
        {{ $t('subtitles.filterAll') }}
      </button>
      <button
        class="sf-status-btn"
        :class="{ active: libStatus === 'missing' }"
        @click="onStatus('missing')"
      >
        <AlertCircle :size="12" />
        {{ $t('subtitles.filterMissing') }}
      </button>
      <button
        class="sf-status-btn"
        :class="{ active: libStatus === 'complete' }"
        @click="onStatus('complete')"
      >
        <Check :size="12" />
        {{ $t('subtitles.filterComplete') }}
      </button>
    </div>

    <div class="sf-divider" aria-hidden="true"></div>

    <!-- Group 3 — tools and view -->
    <div class="sf-group sf-group--tools">
      <button class="sf-tool-btn" :title="$t('subtitles.audit')" @click="emit('audit')">
        <ClipboardCheck :size="14" />
      </button>
      <button
        class="sf-tool-btn"
        :class="{ active: selectMode }"
        :title="$t('subtitles.selectMode')"
        @click="emit('toggle-select-mode')"
      >
        <CheckSquare :size="14" />
      </button>
      <div class="sf-view-toggle">
        <button
          class="sf-view-btn"
          :class="{ active: viewMode === 'grid' }"
          :title="$t('subtitles.gridView')"
          @click="emit('update:viewMode', 'grid')"
        >
          <LayoutGrid :size="14" />
        </button>
        <button
          class="sf-view-btn"
          :class="{ active: viewMode === 'list' }"
          :title="$t('subtitles.listView')"
          @click="emit('update:viewMode', 'list')"
        >
          <List :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { AlertCircle, Check, CheckSquare, ClipboardCheck, LayoutGrid, List } from 'lucide-vue-next'

defineProps({
  libSearch: { type: String, default: '' },
  libType: { type: String, default: '' },
  libLibrary: { type: String, default: '' },
  libStatus: { type: String, default: '' },
  viewMode: { type: String, default: 'grid' },
  selectMode: { type: Boolean, default: false },
  embyLibraries: { type: Array, default: () => [] },
})
const emit = defineEmits([
  'update:libSearch',
  'update:libType',
  'update:libLibrary',
  'update:libStatus',
  'update:viewMode',
  'reset-library',
  'debounce-library',
  'toggle-select-mode',
  'audit',
])

function onStatus(value) {
  emit('update:libStatus', value)
  emit('reset-library')
}
function onSearch(e) {
  emit('update:libSearch', e.target.value)
  emit('debounce-library')
}
function onType(e) {
  emit('update:libType', e.target.value)
  emit('reset-library')
}
function onLibrary(e) {
  emit('update:libLibrary', e.target.value)
  emit('reset-library')
}
</script>

<style scoped>
/* Filter bar — three logical groups separated by thin dividers.
   Group 1: content filters (search + type + library)
   Group 2: subtitle status pills
   Group 3: tools (audit, batch select) + view toggle */
.sf-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 16px;
  flex-wrap: wrap;
  row-gap: 10px;
}
.sf-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sf-group--filters {
  flex: 1 1 auto;
  min-width: 0;
}
.sf-group--status {
  flex: 0 0 auto;
}
.sf-group--tools {
  flex: 0 0 auto;
}
.sf-divider {
  flex: 0 0 auto;
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
  align-self: center;
}

.sf-search-wrap {
  flex: 1 1 auto;
  position: relative;
  min-width: 180px;
  max-width: 360px;
}
.sf-search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--text-base);
  color: rgb(255, 255, 255, 0.2);
}
.sf-search {
  width: 100%;
  height: 36px;
  padding: 0 14px 0 38px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-input);
  font-size: var(--text-sm);
  font-family: inherit;
  box-sizing: border-box;
  background: var(--surface-1);
  color: var(--text-primary);
  outline: none;
}
.sf-search:focus {
  border-color: rgb(var(--accent-rgb), 0.3);
}
.sf-search::placeholder {
  color: rgb(255, 255, 255, 0.2);
}
.sf-select {
  height: 36px;
  padding: 0 30px 0 12px;
  border-radius: var(--radius-input);
  font-size: var(--text-2xs);
  font-family: inherit;
  cursor: pointer;
  background-color: rgb(255, 255, 255, 0.02);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  outline: none;
  box-sizing: border-box;
}
.sf-select option {
  background: var(--mk-chrome-bg);
  color: var(--text-primary);
}
.sf-status-btns {
  gap: 6px;
}
.sf-status-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 14px;
  border-radius: var(--radius-btn);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  font-family: inherit;
  color: rgb(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .sf-status-btn:hover:not(.active) {
    border-color: rgb(255, 255, 255, 0.18);
    transform: translateY(-1px);
  }
}
.sf-status-btn.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: var(--text-primary);
  box-shadow: var(--mk-pill-shadow);
}
.sf-tool-btn {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-input);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(255, 255, 255, 0.02);
  border: 1px solid var(--border-default);
  color: rgb(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all var(--duration-base);
}
.sf-tool-btn.active {
  background: rgb(var(--accent-rgb), 0.1);
  color: var(--accent-300);
  border-color: rgb(var(--accent-rgb), 0.3);
}
.sf-view-toggle {
  display: flex;
  gap: 2px;
  background: var(--surface-1);
  border-radius: var(--radius-btn);
  padding: 2px;
}
.sf-view-btn {
  width: 34px;
  height: 30px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  background: transparent;
  color: rgb(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-base);
}
.sf-view-btn.active {
  background: var(--surface-3);
  color: var(--text-primary);
}

/* ═══ Mobile (≤ 767px) — each group becomes a full-width row ═══
   Dividers are hidden; groups already carry enough visual grouping
   through spacing and the row break. All interactive controls meet
   the 44 × 44 px touch-target convention. */
@media (max-width: 767px) {
  .sf-bar {
    gap: 8px;
    row-gap: 10px;
  }
  .sf-divider {
    display: none;
  }

  /* Group 1 — content filters: search on its own line, both selects share the next one. */
  .sf-group--filters {
    flex: 1 1 100%;
    flex-wrap: wrap;
    gap: 8px;
  }
  .sf-search-wrap {
    flex: 1 1 100%;
    min-width: 0;
    max-width: none;
  }
  .sf-search {
    min-height: 44px;
  }
  .sf-select {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
    min-height: 44px;
  }

  /* Group 2 — status pills spread evenly across a full row. */
  .sf-group--status {
    flex: 1 1 100%;
    gap: 4px;
  }
  .sf-status-btn {
    flex: 1 1 0;
    min-width: 0;
    min-height: 44px;
    justify-content: center;
    padding: 8px 6px;
  }

  /* Group 3 — tools cluster, pushed to the right of its row. */
  .sf-group--tools {
    flex: 1 1 100%;
    justify-content: flex-end;
  }
  .sf-tool-btn {
    min-width: 44px;
    min-height: 44px;
  }
  .sf-view-btn {
    width: auto;
    height: auto;
    min-width: 44px;
    min-height: 44px;
  }
}
</style>
