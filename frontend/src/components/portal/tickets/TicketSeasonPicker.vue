<template>
  <div class="tsp">
    <div v-if="loading" class="tsp-hint">{{ $t('common.loading') }}</div>

    <div v-else-if="!seasons.length" class="tsp-hint">
      {{ $t('portal.tickets.seasonPicker.empty') }}
    </div>

    <template v-else>
      <div class="tsp-summary">
        <span class="tsp-summary-label">{{ summaryLabel }}</span>
        <button v-if="hasAnySelection" type="button" class="tsp-clear" @click="clearAll">
          {{ $t('portal.tickets.seasonPicker.reset') }}
        </button>
      </div>

      <div class="tsp-list">
        <div v-for="s in seasons" :key="s.season_number" class="tsp-season">
          <div class="tsp-season-header" @click="toggleExpanded(s.season_number)">
            <input
              type="checkbox"
              class="tsp-chk"
              :checked="isSeasonFullySelected(s.season_number)"
              :indeterminate.prop="isSeasonPartiallySelected(s.season_number)"
              @click.stop
              @change="toggleSeasonFull(s.season_number)"
            />
            <span class="tsp-season-name">{{ s.name }}</span>
            <span class="tsp-season-meta">
              {{ s.episodes.length }} {{ $t('portal.tickets.seasonPicker.episodes') }}
            </span>
            <span
              class="tsp-chevron"
              :class="{ 'tsp-chevron--open': expanded.has(s.season_number) }"
              aria-hidden="true"
            >
              ▾
            </span>
          </div>

          <div v-if="expanded.has(s.season_number)" class="tsp-episodes">
            <label v-for="ep in s.episodes" :key="ep.episode_number" class="tsp-episode">
              <input
                type="checkbox"
                class="tsp-chk"
                :checked="isEpisodeSelected(s.season_number, ep.episode_number)"
                @change="toggleEpisode(s.season_number, ep.episode_number)"
              />
              <span class="tsp-ep-label">
                E{{ String(ep.episode_number).padStart(2, '0') }}
                <template v-if="ep.name">— {{ ep.name }}</template>
              </span>
            </label>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalTicketEmby } from '@/composables/portal/usePortalTicketEmby'

import '@/assets/styles/portal/ticket-season-picker.css'

const props = defineProps({
  seriesId: { type: String, required: true },
})

/**
 * Emits the normalized payload the backend expects:
 *   { media_type: 'series'|'season'|'episode', selected_seasons: list|null }
 * Empty selection = whole series, no payload list.
 */
const emit = defineEmits(['update:selection'])

const { t } = useI18n()
const { fetchSeriesSeasons } = usePortalTicketEmby()

const seasons = ref([])
const loading = ref(false)
const expanded = ref(new Set())

// Map<seasonNumber, 'full' | Set<episodeNumber>>
const selection = ref(new Map())

watch(
  () => props.seriesId,
  async id => {
    selection.value = new Map()
    expanded.value = new Set()
    seasons.value = []
    if (!id) {
      emitSelection()
      return
    }
    loading.value = true
    try {
      seasons.value = await fetchSeriesSeasons(id)
    } finally {
      loading.value = false
    }
    emitSelection()
  },
  { immediate: true },
)

function toggleExpanded(num) {
  const next = new Set(expanded.value)
  if (next.has(num)) next.delete(num)
  else next.add(num)
  expanded.value = next
}

function isSeasonFullySelected(num) {
  return selection.value.get(num) === 'full'
}

function isSeasonPartiallySelected(num) {
  const sel = selection.value.get(num)
  return sel instanceof Set && sel.size > 0
}

function isEpisodeSelected(seasonNum, epNum) {
  const sel = selection.value.get(seasonNum)
  if (sel === 'full') return true
  return sel instanceof Set && sel.has(epNum)
}

function toggleSeasonFull(num) {
  const next = new Map(selection.value)
  if (next.get(num) === 'full') next.delete(num)
  else next.set(num, 'full')
  selection.value = next
  emitSelection()
}

function toggleEpisode(seasonNum, epNum) {
  const next = new Map(selection.value)
  let sel = next.get(seasonNum)

  // Switching from "full" to per-episode means: keep all episodes
  // ticked, then untick the one the user just toggled.
  if (sel === 'full') {
    const season = seasons.value.find(s => s.season_number === seasonNum)
    sel = new Set((season?.episodes || []).map(e => e.episode_number))
  } else if (!(sel instanceof Set)) {
    sel = new Set()
  } else {
    sel = new Set(sel)
  }

  if (sel.has(epNum)) sel.delete(epNum)
  else sel.add(epNum)

  if (sel.size === 0) next.delete(seasonNum)
  else next.set(seasonNum, sel)

  selection.value = next
  emitSelection()
}

function clearAll() {
  selection.value = new Map()
  emitSelection()
}

const hasAnySelection = computed(() => selection.value.size > 0)

const summaryLabel = computed(() => {
  if (!hasAnySelection.value) {
    return t('portal.tickets.seasonPicker.summaryWhole')
  }
  let seasonCount = 0
  let episodeCount = 0
  for (const [, sel] of selection.value) {
    if (sel === 'full') seasonCount += 1
    else if (sel instanceof Set) episodeCount += sel.size
  }
  if (seasonCount && episodeCount) {
    return t('portal.tickets.seasonPicker.summaryMixed', { s: seasonCount, e: episodeCount })
  }
  if (seasonCount) {
    return t('portal.tickets.seasonPicker.summarySeasons', seasonCount)
  }
  return t('portal.tickets.seasonPicker.summaryEpisodes', episodeCount)
})

function emitSelection() {
  if (!hasAnySelection.value) {
    emit('update:selection', { media_type: 'series', selected_seasons: null })
    return
  }
  const list = []
  let onlyFullSeasons = true
  for (const [seasonNum, sel] of selection.value) {
    if (sel === 'full') {
      list.push({ season_number: seasonNum })
    } else if (sel instanceof Set) {
      onlyFullSeasons = false
      list.push({
        season_number: seasonNum,
        episodes: Array.from(sel).sort((a, b) => a - b),
      })
    }
  }
  list.sort((a, b) => a.season_number - b.season_number)
  emit('update:selection', {
    media_type: onlyFullSeasons ? 'season' : 'episode',
    selected_seasons: list,
  })
}
</script>
