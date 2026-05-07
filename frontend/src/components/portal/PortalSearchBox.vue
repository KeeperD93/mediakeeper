<template>
  <form
    class="pt-search"
    role="search"
    :aria-label="$t('portal.search.title')"
    @submit.prevent="submitSearch"
  >
    <label class="pt-search-shell" :for="inputId">
      <Search class="pt-search-icon" :size="16" />
      <input
        :id="inputId"
        ref="inputRef"
        v-model="query"
        class="pt-search-input"
        type="text"
        autocomplete="off"
        spellcheck="false"
        role="combobox"
        aria-autocomplete="list"
        :aria-expanded="popoverOpen"
        :aria-controls="listboxId"
        :aria-activedescendant="activeOptionId"
        :placeholder="$t('portal.search.placeholder')"
        :aria-label="$t('portal.search.placeholder')"
        @focus="onFocus"
        @blur="onBlur"
        @input="onInput"
        @keydown="onKeydown"
      />
      <button
        class="pt-search-submit"
        type="submit"
        :title="$t('portal.search.submit')"
        :aria-label="$t('portal.search.submit')"
        :disabled="!trimmedQuery"
      >
        <ArrowRight :size="16" :stroke-width="2.2" />
      </button>
    </label>
    <div
      v-if="popoverOpen"
      :id="listboxId"
      ref="popoverRef"
      class="pt-search-popover"
      role="listbox"
      :aria-label="$t('portal.search.suggestionsLabel')"
    >
      <div v-if="recentVisible" class="pt-search-section">
        <div class="pt-search-section-head">
          <span class="pt-search-section-title">{{ $t('portal.search.recentTitle') }}</span>
          <button type="button" class="pt-search-clear" @mousedown.prevent @click="onClearRecents">
            {{ $t('portal.search.clearRecent') }}
          </button>
        </div>
        <button
          v-for="(value, index) in displayedRecents"
          :id="optionId(index)"
          :key="`recent-${value}`"
          type="button"
          role="option"
          class="pt-search-option"
          :class="{ 'pt-search-option--active': activeIndex === index }"
          :aria-selected="activeIndex === index"
          @mousedown.prevent
          @mouseenter="activeIndex = index"
          @click="selectRecent(value)"
        >
          <Clock class="pt-search-option-icon" :size="14" />
          <span class="pt-search-option-text">{{ value }}</span>
        </button>
      </div>
      <div v-else-if="suggestionsVisible" class="pt-search-section">
        <div class="pt-search-section-head">
          <span class="pt-search-section-title">{{ $t('portal.search.suggestionsTitle') }}</span>
        </div>
        <div v-if="showSuggestionsLoading" class="pt-search-empty">
          {{ $t('portal.search.searching') }}
        </div>
        <button
          v-for="(item, index) in freshSuggestions"
          :id="optionId(index)"
          :key="`sugg-${item.media_type}-${item.id}-${index}`"
          type="button"
          role="option"
          class="pt-search-option"
          :class="{ 'pt-search-option--active': activeIndex === index }"
          :aria-selected="activeIndex === index"
          @mousedown.prevent
          @mouseenter="activeIndex = index"
          @click="selectSuggestion(item)"
        >
          <Search class="pt-search-option-icon" :size="14" />
          <span class="pt-search-option-text">
            {{ item.title }}
            <span v-if="item.year" class="pt-search-option-meta">· {{ item.year }}</span>
          </span>
        </button>
        <div v-if="showNoSuggestions" class="pt-search-empty">
          {{ $t('portal.search.noSuggestions') }}
        </div>
      </div>
    </div>
  </form>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Clock, Search } from 'lucide-vue-next'
import { useRecentSearches } from '@/composables/portal/usePortalSearchHistory'
import { usePortalSearchSuggestions } from '@/composables/portal/usePortalSearchSuggestions'

import '@/assets/styles/portal/search-box.css'

// useId() — Vue 3.5 — guarantees an app-wide unique id per component instance,
// stable across renders and SSR. A module-level counter would be local to
// each <script setup> invocation and reset to 0 for every instance.
const uid = useId()
const inputId = `pt-search-${uid}-input`
const listboxId = `pt-search-${uid}-listbox`

const route = useRoute()
const router = useRouter()

const inputRef = ref(null)
const popoverRef = ref(null)
const query = ref('')
const focused = ref(false)
const activeIndex = ref(-1)

const { recents, add: addRecent, clear: clearRecents } = useRecentSearches()
const {
  suggestions,
  pending: suggestionsPending,
  lastQuery: suggestionsLastQuery,
  search: runSuggestions,
  reset: resetSuggestions,
  minLength,
} = usePortalSearchSuggestions()

const trimmedQuery = computed(() => query.value.trim())
const displayedRecents = computed(() => recents.value.slice(0, 5))
const recentVisible = computed(
  () => focused.value && trimmedQuery.value.length < minLength && displayedRecents.value.length > 0,
)
const suggestionsVisible = computed(() => focused.value && trimmedQuery.value.length >= minLength)
const popoverOpen = computed(() => recentVisible.value || suggestionsVisible.value)
// freshSuggestions hides the previous query's results as soon as the user
// edits the input — they're displayed only once a fetch for the *current*
// query has settled. Prevents both stale rows and a premature empty state.
const suggestionsSettled = computed(
  () => !suggestionsPending.value && suggestionsLastQuery.value === trimmedQuery.value,
)
const freshSuggestions = computed(() => (suggestionsSettled.value ? suggestions.value : []))
const showSuggestionsLoading = computed(() => suggestionsVisible.value && suggestionsPending.value)
const showNoSuggestions = computed(
  () => suggestionsVisible.value && suggestionsSettled.value && freshSuggestions.value.length === 0,
)
const activeOptions = computed(() => {
  if (recentVisible.value) return displayedRecents.value.map(value => ({ kind: 'recent', value }))
  if (suggestionsVisible.value)
    return freshSuggestions.value.map(item => ({ kind: 'suggestion', item }))
  return []
})
const activeOptionId = computed(() => {
  if (!popoverOpen.value || activeIndex.value < 0) return undefined
  if (activeIndex.value >= activeOptions.value.length) return undefined
  return optionId(activeIndex.value)
})
function optionId(index) {
  return `${listboxId}-option-${index}`
}

watch(
  () => route.query.q,
  value => {
    query.value = typeof value === 'string' ? value : ''
  },
  { immediate: true },
)

watch(
  () => activeOptions.value.length,
  length => {
    if (length === 0) {
      activeIndex.value = -1
    } else if (activeIndex.value >= length) {
      activeIndex.value = length - 1
    }
  },
)

function onFocus() {
  focused.value = true
  activeIndex.value = -1
}

function onBlur() {
  focused.value = false
  activeIndex.value = -1
}

function onInput() {
  activeIndex.value = -1
  runSuggestions(query.value)
}

function onKeydown(event) {
  switch (event.key) {
    case 'ArrowDown':
      if (!activeOptions.value.length) return
      event.preventDefault()
      activeIndex.value = (activeIndex.value + 1) % activeOptions.value.length
      return
    case 'ArrowUp':
      if (!activeOptions.value.length) return
      event.preventDefault()
      activeIndex.value =
        activeIndex.value <= 0 ? activeOptions.value.length - 1 : activeIndex.value - 1
      return
    case 'Escape':
      if (popoverOpen.value) {
        event.preventDefault()
        focused.value = false
        activeIndex.value = -1
      }
      return
    case 'Enter': {
      const option = activeOptions.value[activeIndex.value]
      if (option) {
        event.preventDefault()
        if (option.kind === 'recent') selectRecent(option.value)
        else selectSuggestion(option.item)
      }
      return
    }
    default:
      return
  }
}

function onClearRecents() {
  clearRecents()
  activeIndex.value = -1
  inputRef.value?.focus()
}

async function selectRecent(value) {
  query.value = value
  resetSuggestions()
  await goToSearch(value)
}

async function selectSuggestion(item) {
  if (!item || !item.title) return
  query.value = item.title
  resetSuggestions()
  await goToSearch(item.title)
}

async function submitSearch() {
  const value = trimmedQuery.value
  if (!value) {
    inputRef.value?.focus()
    return
  }
  resetSuggestions()
  await goToSearch(value)
}

async function goToSearch(rawValue) {
  const value = (rawValue || '').trim()
  if (!value) return

  addRecent(value)

  focused.value = false
  activeIndex.value = -1
  inputRef.value?.blur()

  const target = { name: 'portal-search', query: { q: value } }

  if (route.name === 'portal-search' && route.query.q === value) {
    await nextTick()
    return
  }

  if (route.name === 'portal-search') {
    await router.replace(target)
    return
  }

  await router.push(target)
}

onUnmounted(() => {
  resetSuggestions()
})
</script>
