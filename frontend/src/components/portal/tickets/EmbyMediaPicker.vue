<template>
  <div ref="pickerRoot" class="emp" :class="{ 'emp--has-selection': !!modelValue }">
    <!-- Selected hit summary: poster + title + reset button -->
    <div v-if="modelValue" class="emp-selected">
      <img
        :src="`/api/emby/image/${modelValue.poster_id}?type=Primary`"
        class="emp-selected-poster"
        :alt="modelValue.title"
        loading="lazy"
        @error="$event.target.style.display = 'none'"
      />
      <div class="emp-selected-meta">
        <div class="emp-selected-title">{{ modelValue.title }}</div>
        <div class="emp-selected-sub">
          <span class="emp-kind-pill" :class="`emp-kind--${modelValue.type}`">
            {{ $t(`portal.tickets.picker.kind.${modelValue.type}`) }}
          </span>
          <span v-if="modelValue.year" class="emp-year">{{ modelValue.year }}</span>
        </div>
      </div>
      <button
        type="button"
        class="emp-clear"
        :aria-label="$t('portal.tickets.picker.clear')"
        @click="onClear"
      >
        ✕
      </button>
    </div>

    <!-- Search input + dropdown when no selection -->
    <div v-else class="emp-search">
      <input
        ref="inputEl"
        v-model="query"
        type="text"
        class="emp-input"
        :placeholder="$t('portal.tickets.picker.placeholder')"
        autocomplete="off"
        spellcheck="false"
        :aria-expanded="dropdownOpen"
        aria-controls="emp-listbox"
        role="combobox"
        @input="onInput"
        @keydown.down.prevent="moveCursor(1)"
        @keydown.up.prevent="moveCursor(-1)"
        @keydown.enter.prevent="onEnter"
        @keydown.esc="onEscape"
        @focus="onFocus"
      />
      <div v-if="searching" class="emp-spinner" aria-hidden="true" />

      <div v-if="dropdownOpen" id="emp-listbox" class="emp-dropdown" role="listbox">
        <p v-if="query.length < MIN_QUERY_LENGTH" class="emp-hint">
          {{ $t('portal.tickets.picker.minChars', { n: MIN_QUERY_LENGTH }) }}
        </p>
        <p v-else-if="searching && !results.length" class="emp-hint">
          {{ $t('common.loading') }}
        </p>
        <p v-else-if="!results.length" class="emp-hint">
          {{ $t('portal.tickets.picker.noResults') }}
        </p>
        <ul v-else class="emp-list">
          <li
            v-for="(hit, idx) in results"
            :key="hit.id"
            :class="['emp-hit', { 'emp-hit--active': idx === cursor }]"
            role="option"
            :aria-selected="idx === cursor"
            @mouseenter="cursor = idx"
            @mousedown.prevent="select(hit)"
          >
            <img
              :src="`/api/emby/image/${hit.poster_id}?type=Primary`"
              class="emp-hit-poster"
              :alt="hit.title"
              loading="lazy"
              @error="$event.target.style.display = 'none'"
            />
            <div class="emp-hit-meta">
              <div class="emp-hit-title">{{ hit.title }}</div>
              <div class="emp-hit-sub">
                <span class="emp-kind-pill" :class="`emp-kind--${hit.type}`">
                  {{ $t(`portal.tickets.picker.kind.${hit.type}`) }}
                </span>
                <span v-if="hit.year" class="emp-year">{{ hit.year }}</span>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { usePortalTicketEmby } from '@/composables/portal/usePortalTicketEmby'

defineProps({
  /** Currently selected hit, or null. Shape matches the Emby search response. */
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const { results, searching, searchDebounced, clearResults, MIN_QUERY_LENGTH } =
  usePortalTicketEmby()

const query = ref('')
const inputEl = ref(null)
const pickerRoot = ref(null)
const dropdownOpen = ref(false)
const cursor = ref(0)

function closeIfOutside(event) {
  if (!pickerRoot.value || !dropdownOpen.value) return
  if (!pickerRoot.value.contains(event.target)) {
    dropdownOpen.value = false
  }
}

// mousedown (not click) so a suggestion's mousedown.prevent select()
// runs BEFORE the outside-close handler fires.
onMounted(() => {
  document.addEventListener('mousedown', closeIfOutside)
  document.addEventListener('touchstart', closeIfOutside, { passive: true })
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', closeIfOutside)
  document.removeEventListener('touchstart', closeIfOutside)
})

watch(results, () => {
  cursor.value = 0
})

function onInput() {
  dropdownOpen.value = true
  searchDebounced(query.value)
}

function onFocus() {
  dropdownOpen.value = true
  // Re-trigger if the user comes back with a non-trivial query already typed.
  if (query.value.trim().length >= MIN_QUERY_LENGTH && !results.value.length) {
    searchDebounced(query.value)
  }
}

function onEscape() {
  dropdownOpen.value = false
}

function moveCursor(delta) {
  if (!results.value.length) return
  dropdownOpen.value = true
  const max = results.value.length
  cursor.value = (cursor.value + delta + max) % max
}

function onEnter() {
  if (!dropdownOpen.value) return
  const hit = results.value[cursor.value]
  if (hit) select(hit)
}

function select(hit) {
  emit('update:modelValue', hit)
  dropdownOpen.value = false
  clearResults()
  query.value = ''
}

function onClear() {
  emit('update:modelValue', null)
  query.value = ''
  clearResults()
  nextTick(() => inputEl.value?.focus())
}
</script>

<style scoped>
.emp {
  position: relative;
  width: 100%;
}

.emp-selected {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--portal-border-default);
  border-radius: var(--radius-card);
}
.emp-selected-poster {
  width: 48px;
  height: 72px;
  flex-shrink: 0;
  object-fit: cover;
  border-radius: var(--radius-input);
  background: var(--bg-secondary);
}
.emp-selected-meta {
  flex: 1;
  min-width: 0;
}
.emp-selected-title {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.emp-selected-sub {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
}

.emp-clear {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid var(--portal-border-default);
  color: var(--text-muted);
  font-size: var(--portal-text-sm);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    color var(--portal-dur-base) var(--portal-ease-emphasis),
    border-color var(--portal-dur-base) var(--portal-ease-emphasis),
    background var(--portal-dur-base) var(--portal-ease-emphasis);
}
@media (hover: hover) {
  .emp-clear:hover {
    color: var(--text-primary);
    border-color: var(--text-muted);
    background: var(--bg-secondary);
  }
}

.emp-search {
  position: relative;
}
.emp-input {
  width: 100%;
  min-height: 44px;
  background: var(--bg-tertiary);
  border: 1px solid var(--portal-border-default);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 10px 36px 10px 12px;
  font-size: var(--portal-text-sm);
}
.emp-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--mk-pill-shadow-sm);
}

.emp-spinner {
  position: absolute;
  right: 12px;
  top: 50%;
  width: 14px;
  height: 14px;
  border: 2px solid var(--portal-border-default);
  border-top-color: var(--accent);
  border-radius: 999px;
  transform: translateY(-50%);
  animation: emp-spin 0.8s linear infinite;
}
@keyframes emp-spin {
  to {
    transform: translateY(-50%) rotate(360deg);
  }
}

.emp-dropdown {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  z-index: 30;
  max-height: 280px;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--portal-border-default);
  border-radius: var(--radius-card);
  box-shadow: var(--portal-shadow-md);
}

.emp-hint {
  padding: 14px 16px;
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
  text-align: center;
}

.emp-list {
  list-style: none;
  margin: 0;
  padding: 4px;
}

.emp-hit {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px;
  min-height: 44px;
  border-radius: var(--radius-input);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background var(--portal-dur-fast) var(--portal-ease-emphasis);
}
.emp-hit--active {
  background: var(--bg-tertiary);
}
.emp-hit-poster {
  width: 38px;
  height: 57px;
  flex-shrink: 0;
  object-fit: cover;
  border-radius: var(--radius-input);
  background: var(--bg-tertiary);
}
.emp-hit-meta {
  flex: 1;
  min-width: 0;
}
.emp-hit-title {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.emp-hit-sub {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 2px;
}

.emp-kind-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-wide);
}
.emp-kind--movie {
  background: rgb(var(--portal-color-info-rgb), 0.15);
  color: var(--portal-color-info-light);
}
.emp-kind--series {
  background: rgb(var(--portal-color-premium-rgb), 0.15);
  color: var(--portal-color-premium-soft);
}
.emp-year {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}

@media (min-width: 768px) {
  .emp-selected-poster {
    width: 56px;
    height: 84px;
  }
  .emp-clear {
    width: 32px;
    height: 32px;
  }
  .emp-hit-poster {
    width: 44px;
    height: 66px;
  }
  .emp-dropdown {
    max-height: 360px;
  }
}
</style>
