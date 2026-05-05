<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="visible" class="so-overlay" @click.self="$emit('close')">
        <div class="so-modal so-solid">
          <!-- Header -->
          <div class="so-header">
            <img
              :src="'/api/emby/image/' + seriesPoster"
              class="so-poster"
              alt=""
              @error="$event.target.style.display = 'none'"
            />
            <div class="so-header-info">
              <h2 class="so-title">{{ seriesName }}</h2>
              <span class="so-count">{{ episodes.length }} {{ $t('subtitles.episodes') }}</span>
            </div>
            <button class="so-close" @click="$emit('close')">
              <X :size="16" />
            </button>
          </div>

          <!-- Seasons / Episodes -->
          <div class="so-episodes">
            <template v-for="s in seasons" :key="s.num">
              <!-- Season header (always visible, click to expand) -->
              <div class="so-season-header" @click="toggleSeason(s.num)">
                <ChevronDown
                  :class="{ 'so-chev-open': openSeasons[s.num] }"
                  class="so-season-chev"
                  :size="14"
                  :stroke-width="2.5"
                />
                <span class="so-season-label">{{ $t('subtitles.season') }} {{ s.num }}</span>
                <span class="so-season-count">{{ s.episodes.length }} ep</span>
                <div class="so-ep-pills">
                  <span
                    v-for="(has, lang) in s.globalTags"
                    :key="lang"
                    class="sg-pill"
                    :class="[has ? 'sg-pill-ok' : 'sg-pill-miss']"
                    :style="pillStyle(lang, has)"
                  >
                    <span v-if="has" class="sg-pill-dot" :style="dotStyle(lang)" />
                    {{ langShort(lang) }}
                  </span>
                </div>
              </div>
              <!-- Episodes (collapsed by default, expanded on season click) -->
              <template v-if="openSeasons[s.num]">
                <template v-for="ep in s.episodes" :key="ep.item_id">
                  <div
                    class="so-ep-row so-ep-indent"
                    :class="{ 'so-ep-active': selectedEp && selectedEp.item_id === ep.item_id }"
                    @click="selectEpisode(ep)"
                  >
                    <span class="so-ep-tag">S{{ ep.season || 0 }}E{{ ep.episode || 0 }}</span>
                    <span class="so-ep-name">{{ ep.name }}</span>
                    <div class="so-ep-pills">
                      <span
                        v-for="(has, lang) in ep.subtitle_status"
                        :key="lang"
                        class="sg-pill"
                        :class="[has ? 'sg-pill-ok' : 'sg-pill-miss']"
                        :style="pillStyle(lang, has)"
                      >
                        <span v-if="has" class="sg-pill-dot" :style="dotStyle(lang)" />
                        {{ langShort(lang) }}
                      </span>
                    </div>
                    <span
                      v-if="selectedEp && selectedEp.item_id === ep.item_id && epSubs === null"
                      class="mk-spin so-ep-loading"
                    />
                    <ChevronRight
                      v-else
                      class="so-ep-chevron"
                      :class="{
                        'so-ep-chevron-open':
                          selectedEp && selectedEp.item_id === ep.item_id && epSubs !== null,
                      }"
                      :size="14"
                    />
                  </div>

                  <!-- Inline detail panel — only opens VISUALLY once ffprobe data
                       is loaded, so the whole content appears at once in a single
                       smooth slide-down (no mid-animation reflow). -->
                  <div
                    class="so-detail-slot"
                    :class="{
                      'so-detail-slot--open':
                        selectedEp && selectedEp.item_id === ep.item_id && epSubs !== null,
                    }"
                  >
                    <div class="so-detail-clip">
                      <div
                        v-if="selectedEp && selectedEp.item_id === ep.item_id"
                        class="so-detail so-solid"
                      >
                        <div class="so-detail-header">
                          <span class="so-detail-tag">
                            S{{ selectedEp.season }}E{{ selectedEp.episode }}
                          </span>
                          <span class="so-detail-name">{{ selectedEp.name }}</span>
                          <button class="so-detail-close" @click="selectedEp = null">
                            <X :size="12" />
                          </button>
                        </div>

                        <!-- Existing subs -->
                        <div class="sd-section">
                          <div class="sd-title-row">
                            <h4 class="sd-title">{{ $t('subtitles.existingSubs') }}</h4>
                            <button
                              v-if="removeSelection.length"
                              class="sd-batch-del"
                              :disabled="removing"
                              @click="batchRemove"
                            >
                              <span v-if="removing" class="mk-spin mk-spin-10" />
                              <template v-else>
                                {{
                                  $t('subtitles.removeSelected', { count: removeSelection.length })
                                }}
                              </template>
                            </button>
                          </div>
                          <div v-if="epSubs === null" class="sd-loading">
                            <span class="mk-spin mk-spin-14" />
                          </div>
                          <div v-else-if="!epSubs.length" class="sd-empty">
                            {{ $t('subtitles.noSubs') }}
                          </div>
                          <div v-else class="sd-sub-list">
                            <div v-for="s2 in epSubs" :key="s2.index" class="sd-sub-row">
                              <input
                                v-if="!s2.is_external"
                                type="checkbox"
                                class="sd-sub-check"
                                :checked="removeSelection.includes(s2.index)"
                                :disabled="removing"
                                @change="toggleRemove(s2.index)"
                              />
                              <span class="sd-sub-lang">{{ s2.language.toUpperCase() }}</span>
                              <span v-if="s2.title" class="sd-sub-title">{{ s2.title }}</span>
                              <span class="sd-sub-codec">{{ s2.codec }}</span>
                              <span
                                class="sd-sub-badge"
                                :class="s2.is_external ? 'badge-ext' : 'badge-emb'"
                              >
                                {{
                                  s2.is_external
                                    ? $t('subtitles.external')
                                    : $t('subtitles.embedded')
                                }}
                              </span>
                              <span v-if="s2.is_forced" class="sd-sub-badge badge-forced">
                                {{ $t('subtitles.forced') }}
                              </span>
                              <span v-if="s2.is_image_based" class="sd-sub-badge badge-pgs">
                                PGS
                              </span>
                              <button
                                v-if="s2.is_external && s2.path"
                                class="sd-sub-del"
                                :disabled="removing"
                                :title="$t('common.delete')"
                                @click="deleteSub(s2)"
                              >
                                <Trash2 :size="12" />
                              </button>
                            </div>
                          </div>
                        </div>

                        <!-- Audio tracks -->
                        <div v-if="epAudio && epAudio.length" class="sd-section">
                          <h4 class="sd-title">{{ $t('subtitles.audioTracks') }}</h4>
                          <div class="sd-sub-list">
                            <div v-for="a in epAudio" :key="a.index" class="sd-sub-row">
                              <input
                                type="checkbox"
                                class="sd-sub-check"
                                :checked="removeSelection.includes(a.index)"
                                :disabled="removing"
                                @change="toggleRemove(a.index)"
                              />
                              <span class="sd-sub-lang">{{ a.language.toUpperCase() }}</span>
                              <span v-if="a.title" class="sd-sub-title">{{ a.title }}</span>
                              <span class="sd-sub-codec">{{ a.codec }}</span>
                              <span v-if="a.channels" class="sd-sub-badge badge-audio">
                                {{ formatChannels(a.channels) }}
                              </span>
                              <span v-if="a.is_default" class="sd-sub-badge badge-default">
                                Default
                              </span>
                            </div>
                          </div>
                        </div>

                        <!-- Search + results -->
                        <div class="sd-section">
                          <button class="so-search-btn" :disabled="epSearching" @click="searchEp">
                            <span v-if="epSearching" class="mk-spin mk-spin-12" />
                            <template v-else>&#8981; {{ $t('subtitles.searchSubs') }}</template>
                          </button>

                          <!-- Results slot — same smooth grid-template-rows animation as the
                             episode detail panel. Stays closed while epSearching so the
                             panel doesn't grow mid-animation. -->
                          <div
                            class="so-detail-slot"
                            :class="{
                              'so-detail-slot--open': !epSearching && epResults.length > 0,
                            }"
                          >
                            <div class="so-detail-clip">
                              <div class="so-results-inner">
                                <div v-if="epResults.length >= 2" class="sub-cmp-hint">
                                  <span>{{ $t('subtitles.selectToCompare') }}</span>
                                  <button
                                    v-if="compareSelection.length === 2"
                                    class="sub-cmp-go"
                                    @click="showComparator = true"
                                  >
                                    {{ $t('subtitles.compare') }}
                                  </button>
                                </div>
                                <div class="sd-os-results">
                                  <SubOsResultRow
                                    v-for="r in epResults"
                                    :key="r.file_id"
                                    :result="r"
                                    :downloading="downloading === r.file_id"
                                    :selectable="epResults.length >= 2"
                                    :selected="
                                      compareSelection.some(s3 => s3.file_id === r.file_id)
                                    "
                                    @download="downloadEp($event)"
                                    @select="toggleCompareSelect(r)"
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                          <SubDesyncBanner
                            v-if="lastDlResult"
                            :desync="lastDlResult.desync"
                            :encoding="lastDlResult.encoding"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
              </template>
            </template>
          </div>
        </div>
        <SubComparatorModal
          v-if="showComparator"
          :visible="showComparator"
          :file-a="compareSelection[0] || null"
          :file-b="compareSelection[1] || null"
          @close="showComparator = false"
        />
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, toRef, watch } from 'vue'
import SubOsResultRow from './SubOsResultRow.vue'
import SubDesyncBanner from './SubDesyncBanner.vue'
import SubComparatorModal from './SubComparatorModal.vue'
import { useEpisodeSubDetail } from '@/composables/useEpisodeSubDetail'
import { ChevronDown, ChevronRight, Trash2, X } from 'lucide-vue-next'

import '@/assets/styles/subtitles/series-overlay.css'

const props = defineProps({
  visible: Boolean,
  seriesName: { type: String, default: '' },
  seriesPoster: { type: String, default: '' },
  episodes: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'select-episode', 'downloaded'])

// Group episodes by season with a derived `globalTags` set: a language
// tag appears green at the season level only if every episode in that
// season has it.
const openSeasons = reactive({})
const seasons = computed(() => {
  const map = new Map()
  for (const ep of props.episodes) {
    const num = ep.season || 1
    if (!map.has(num)) map.set(num, { num, episodes: [] })
    map.get(num).episodes.push(ep)
  }
  const list = [...map.values()].sort((a, b) => a.num - b.num)
  for (const s of list) {
    const langs = new Set()
    s.episodes.forEach(ep => Object.keys(ep.subtitle_status || {}).forEach(l => langs.add(l)))
    s.globalTags = {}
    for (const lang of langs) {
      s.globalTags[lang] = s.episodes.every(ep => ep.subtitle_status?.[lang])
    }
    s.episodes.sort((a, b) => (a.episode || 0) - (b.episode || 0))
  }
  return list
})
function toggleSeason(num) {
  openSeasons[num] = !openSeasons[num]
}

const {
  selectedEp,
  epSubs,
  epAudio,
  epResults,
  epSearching,
  downloading,
  lastDlResult,
  removing,
  removeSelection,
  compareSelection,
  showComparator,
  resetEpisode,
  toggleCompareSelect,
  searchEp,
  downloadEp,
  deleteSub,
  toggleRemove,
  batchRemove,
} = useEpisodeSubDetail({
  seriesNameRef: toRef(props, 'seriesName'),
  onDownloaded: () => emit('downloaded'),
})

function selectEpisode(ep) {
  // Click on the already-open episode → close the inline detail panel.
  selectedEp.value = selectedEp.value && selectedEp.value.item_id === ep.item_id ? null : ep
}

watch(
  () => props.visible,
  v => {
    if (!v) resetEpisode()
  },
)

// Stable HSL per language code, memoised.
const _langColorCache = {}
function langColor(code) {
  if (_langColorCache[code]) return _langColorCache[code]
  let hash = 0
  for (let i = 0; i < code.length; i++) hash = code.charCodeAt(i) + ((hash << 5) - hash)
  const hue = ((hash % 360) + 360) % 360
  _langColorCache[code] = {
    hue,
    color: `hsl(${hue}, 65%, 70%)`,
    bg: `hsla(${hue}, 65%, 55%, 0.15)`,
  }
  return _langColorCache[code]
}
function pillStyle(lang, has) {
  if (!has) return {}
  const c = langColor(lang)
  return { background: c.bg, color: c.color, borderColor: 'transparent' }
}
function dotStyle(lang) {
  return { background: langColor(lang).color }
}

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

function formatChannels(ch) {
  if (ch === 1) return 'Mono'
  if (ch === 2) return 'Stereo'
  if (ch === 6) return '5.1'
  if (ch === 8) return '7.1'
  return `${ch}ch`
}
</script>
