<template>
  <div class="sg-wrapper">
    <!-- ═══ GRID MODE ═══ -->
    <div
      v-if="mode === 'grid'"
      class="sg-card"
      :class="{ 'sg-selected': expanded, 'sg-hovered': isHovered }"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
      @click="$emit('toggle')"
    >
      <!-- Poster -->
      <div class="sg-poster-wrap">
        <img
          :src="'/api/emby/image/' + (item.poster_id || item.item_id)"
          class="sg-poster"
          alt=""
          loading="lazy"
          @error="$event.target.style.display = 'none'"
        />
        <div class="sg-gradient" />

        <!-- Tag badge -->
        <span class="sg-tag" :class="item.type === 'Movie' ? 'sg-tag-movie' : 'sg-tag-ep'">
          {{
            item.type === 'Movie'
              ? $t('subtitles.typeMovie')
              : item._isGroup
                ? `${item._episodeCount} ep`
                : `S${item.season || 0}E${item.episode || 0}`
          }}
        </span>

        <!-- Missing dot -->
        <span v-if="hasMissing" class="sg-missing-dot" />

        <!-- Select checkbox (batch mode) -->
        <input
          v-if="selectable"
          type="checkbox"
          class="sg-check"
          :checked="isSelected"
          @click.stop
          @change.stop="$emit('select-item')"
        />

        <!-- Bottom info -->
        <div class="sg-bottom">
          <div class="sg-title">{{ item.series_name || item.name }}</div>
          <div v-if="item.series_name" class="sg-episode">{{ item.name }}</div>
          <div class="sg-pills">
            <span
              v-for="(has, lang) in item.subtitle_status"
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
      </div>

      <!-- Expanded action bar (not for groups — groups open overlay) -->
      <div v-if="expanded && !item._isGroup" class="sg-actions">
        <button class="sg-action-btn sg-action-search" @click.stop="$emit('search')">
          <span v-if="searching" class="mk-spin mk-spin-11" />
          <template v-else>&#8981; {{ $t('subtitles.searchSubs') }}</template>
        </button>
        <button
          v-if="item.type === 'Episode' && item.series_name"
          class="sg-action-btn sg-action-matrix"
          @click.stop="$emit('show-matrix', item)"
        >
          &#9783; {{ $t('subtitles.seriesMatrix') }}
        </button>
      </div>
    </div>

    <!-- ═══ LIST MODE ═══ -->
    <div
      v-else
      class="sl-row"
      :class="{ 'sl-hovered': isHovered, 'sl-expanded': expanded }"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
      @click="$emit('toggle')"
    >
      <input
        v-if="selectable"
        type="checkbox"
        class="sl-check"
        :checked="isSelected"
        @click.stop
        @change.stop="$emit('select-item')"
      />
      <img
        :src="'/api/emby/image/' + (item.poster_id || item.item_id)"
        class="sl-poster"
        alt=""
        loading="lazy"
        @error="$event.target.style.display = 'none'"
      />
      <div class="sl-info">
        <div class="sl-name">
          {{
            item._isGroup
              ? item.name
              : (item.series_name ? item.series_name + ' — ' : '') + item.name
          }}
        </div>
        <div v-if="!item._isGroup && item.series_name" class="sl-ep">{{ item.name }}</div>
      </div>
      <span class="sl-tag" :class="item.type === 'Movie' ? 'sl-tag-movie' : 'sl-tag-ep'">
        {{
          item.type === 'Movie'
            ? $t('subtitles.typeMovie')
            : item._isGroup
              ? `${item._episodeCount} ep`
              : `S${item.season || 0}E${item.episode || 0}`
        }}
      </span>
      <div class="sl-pills">
        <span
          v-for="(has, lang) in item.subtitle_status"
          :key="lang"
          class="sg-pill"
          :class="[has ? 'sg-pill-ok' : 'sg-pill-miss']"
          :style="pillStyle(lang, has)"
        >
          <span v-if="has" class="sg-pill-dot" :style="dotStyle(lang)" />
          {{ langShort(lang) }}
        </span>
      </div>
      <SubOsBadge v-if="osCount" :count="osCount" />
    </div>

    <!-- ═══ DETAIL PANEL (shared, below card or row) ═══ -->
    <transition name="sub-slide">
      <div
        v-if="expanded && !item._isGroup && (subs !== null || results.length)"
        class="sd-panel sd-solid"
      >
        <!-- Existing subtitles -->
        <div class="sd-section">
          <h4 class="sd-title">{{ $t('subtitles.existingSubs') }}</h4>
          <div v-if="subs === null" class="sd-loading"><span class="mk-spin mk-spin-14" /></div>
          <div v-else-if="!subs.length" class="sd-empty">{{ $t('subtitles.noSubs') }}</div>
          <div v-else class="sd-sub-list">
            <div v-for="s in subs" :key="s.index" class="sd-sub-row">
              <span class="sd-sub-lang">{{ s.language.toUpperCase() }}</span>
              <span class="sd-sub-codec">{{ s.codec }}</span>
              <span class="sd-sub-badge" :class="s.is_external ? 'badge-ext' : 'badge-emb'">
                {{ s.is_external ? $t('subtitles.external') : $t('subtitles.embedded') }}
              </span>
              <span v-if="s.is_forced" class="sd-sub-badge badge-forced">
                {{ $t('subtitles.forced') }}
              </span>
              <span v-if="s.is_image_based" class="sd-sub-badge badge-pgs">PGS</span>
              <button
                v-if="s.is_external && s.path"
                class="sd-sub-del"
                :title="$t('common.delete')"
                @click.stop="$emit('delete-sub', s)"
              >
                <Trash2 :size="12" />
              </button>
              <button
                v-if="!s.is_external"
                class="sd-sub-del"
                :title="$t('subtitles.removeStream')"
                @click.stop="
                  $emit('remove-stream', {
                    item_id: item.item_id,
                    stream_index: s.index,
                    type: STREAM_TYPE.SUBTITLE,
                    language: s.language,
                  })
                "
              >
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
        </div>

        <!-- Audio tracks -->
        <div v-if="audioStreams && audioStreams.length" class="sd-section">
          <h4 class="sd-title">{{ $t('subtitles.audioTracks') }}</h4>
          <div class="sd-sub-list">
            <div v-for="a in audioStreams" :key="a.index" class="sd-sub-row">
              <span class="sd-sub-lang">{{ a.language.toUpperCase() }}</span>
              <span class="sd-sub-codec">{{ a.codec }}</span>
              <span v-if="a.channels" class="sd-sub-badge badge-audio">
                {{ formatChannels(a.channels) }}
              </span>
              <span v-if="a.is_default" class="sd-sub-badge badge-default">Default</span>
              <button
                class="sd-sub-del"
                :title="$t('subtitles.removeStream')"
                @click.stop="
                  $emit('remove-stream', {
                    item_id: item.item_id,
                    stream_index: a.index,
                    type: STREAM_TYPE.AUDIO,
                    language: a.language,
                  })
                "
              >
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
        </div>

        <!-- Search results -->
        <div v-if="results.length || searching" class="sd-section">
          <div v-if="results.length >= 2" class="sub-cmp-hint">
            <span>{{ $t('subtitles.selectToCompare') }}</span>
            <button
              v-if="compareSelection.length === 2"
              class="sub-cmp-go"
              @click.stop="$emit('compare', compareSelection)"
            >
              {{ $t('subtitles.compare') }}
            </button>
          </div>
          <div class="sd-os-results">
            <SubOsResultRow
              v-for="r in results"
              :key="r.file_id"
              :result="r"
              :downloading="downloadingId === r.file_id"
              :selectable="results.length >= 2"
              :selected="compareSelection.some(s => s.file_id === r.file_id)"
              @download="$emit('download', $event)"
              @select="toggleCompareSelect($event)"
            />
          </div>
          <SubDesyncBanner
            v-if="lastDownloadResult"
            :desync="lastDownloadResult.desync"
            :encoding="lastDownloadResult.encoding"
          />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SubOsResultRow from './SubOsResultRow.vue'
import SubOsBadge from './SubOsBadge.vue'
import SubDesyncBanner from './SubDesyncBanner.vue'
import { Trash2 } from 'lucide-vue-next'
import { STREAM_TYPE } from '@/constants/subtitles'

import '@/assets/styles/subtitles/library-item.css'

const props = defineProps({
  item: { type: Object, required: true },
  mode: { type: String, default: 'grid' }, // 'grid' | 'list'
  expanded: { type: Boolean, default: false },
  subs: { type: Array, default: null },
  results: { type: Array, default: () => [] },
  searching: { type: Boolean, default: false },
  downloadingId: { type: [Number, null], default: null },
  osCount: { type: [Number, null], default: null },
  lastDownloadResult: { type: Object, default: null },
  selectable: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  audioStreams: { type: Array, default: () => [] },
})
defineEmits([
  'toggle',
  'search',
  'download',
  'delete-sub',
  'remove-stream',
  'show-matrix',
  'compare',
  'select-item',
])

const isHovered = ref(false)
const compareSelection = ref([])

const hasMissing = computed(() => !Object.values(props.item.subtitle_status || {}).every(v => v))

function langShort(code) {
  return (
    {
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
    }[code] || code.slice(0, 2).toUpperCase()
  )
}

// Couleur stable par code langue (HSL)
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

function formatChannels(ch) {
  if (ch === 1) return 'Mono'
  if (ch === 2) return 'Stereo'
  if (ch === 6) return '5.1'
  if (ch === 8) return '7.1'
  return `${ch}ch`
}

function toggleCompareSelect(result) {
  const idx = compareSelection.value.findIndex(s => s.file_id === result.file_id)
  if (idx >= 0) {
    compareSelection.value.splice(idx, 1)
  } else {
    if (compareSelection.value.length >= 2) compareSelection.value.shift()
    compareSelection.value.push(result)
  }
}
</script>
