<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="visible && item" class="si-overlay" @click.self="$emit('close')">
        <div class="si-modal">
          <!-- Header -->
          <div class="si-header">
            <img :src="'/api/emby/image/' + (item.poster_id || item.item_id)" class="si-poster" alt="" @error="$event.target.style.display='none'" />
            <div class="si-header-info">
              <h2 class="si-title">{{ item.series_name ? item.series_name + ' — ' : '' }}{{ item.name }}</h2>
              <span class="si-meta">
                <span v-if="item.type === 'Episode'" class="si-tag">S{{ item.season || 0 }}E{{ item.episode || 0 }}</span>
                <span v-else class="si-tag si-tag-movie">{{ $t('subtitles.typeMovie') }}</span>
                <span v-if="item.year" class="si-year">{{ item.year }}</span>
              </span>
            </div>
            <button class="si-close" @click="$emit('close')">
              <X :size="16" />
            </button>
          </div>

          <!-- Existing subtitles -->
          <div class="sd-section">
            <div class="sd-title-row">
              <h4 class="sd-title">{{ $t('subtitles.existingSubs') }}</h4>
              <button v-if="removeSelection.length" class="sd-batch-del" :disabled="removing" @click="batchRemove">
                <span v-if="removing" class="mk-spin mk-spin-10" />
                <template v-else>{{ $t('subtitles.removeSelected', { count: removeSelection.length }) }}</template>
              </button>
            </div>
            <div v-if="subs === null" class="sd-loading"><span class="mk-spin mk-spin-14" /></div>
            <div v-else-if="!subs.length" class="sd-empty">{{ $t('subtitles.noSubs') }}</div>
            <div v-else class="sd-sub-list">
              <div v-for="s in subs" :key="s.index" class="sd-sub-row">
                <input v-if="!s.is_external" type="checkbox" class="sd-sub-check" :checked="removeSelection.includes(s.index)" :disabled="removing" @change="toggleRemove(s.index)" />
                <span class="sd-sub-lang">{{ s.language.toUpperCase() }}</span>
                <span v-if="s.title" class="sd-sub-title">{{ s.title }}</span>
                <span class="sd-sub-codec">{{ s.codec }}</span>
                <span class="sd-sub-badge" :class="s.is_external ? 'badge-ext' : 'badge-emb'">{{ s.is_external ? $t('subtitles.external') : $t('subtitles.embedded') }}</span>
                <span v-if="s.is_forced" class="sd-sub-badge badge-forced">{{ $t('subtitles.forced') }}</span>
                <span v-if="s.is_image_based" class="sd-sub-badge badge-pgs">PGS</span>
                <button v-if="s.is_external && s.path" class="sd-sub-del" :disabled="removing" :title="$t('common.delete')" @click="deleteSub(s)">
                  <Trash2 :size="12" />
                </button>
              </div>
            </div>
          </div>

          <!-- Audio tracks -->
          <div v-if="audio && audio.length" class="sd-section">
            <h4 class="sd-title">{{ $t('subtitles.audioTracks') }}</h4>
            <div class="sd-sub-list">
              <div v-for="a in audio" :key="a.index" class="sd-sub-row">
                <input type="checkbox" class="sd-sub-check" :checked="removeSelection.includes(a.index)" :disabled="removing" @change="toggleRemove(a.index)" />
                <span class="sd-sub-lang">{{ a.language.toUpperCase() }}</span>
                <span v-if="a.title" class="sd-sub-title">{{ a.title }}</span>
                <span class="sd-sub-codec">{{ a.codec }}</span>
                <span v-if="a.channels" class="sd-sub-badge badge-audio">{{ formatChannels(a.channels) }}</span>
                <span v-if="a.is_default" class="sd-sub-badge badge-default">Default</span>
              </div>
            </div>
          </div>

          <!-- Search + results -->
          <div class="sd-section">
            <button class="si-search-btn" :disabled="searching" @click="searchItem">
              <span v-if="searching" class="mk-spin mk-spin-12" />
              <template v-else>&#8981; {{ $t('subtitles.searchSubs') }}</template>
            </button>
            <div v-if="results.length >= 2" class="sub-cmp-hint">
              <span>{{ $t('subtitles.selectToCompare') }}</span>
              <button v-if="compareSelection.length === 2" class="sub-cmp-go" @click="showComparator = true">
                {{ $t('subtitles.compare') }}
              </button>
            </div>
            <div v-if="results.length" class="sd-os-results">
              <SubOsResultRow
                v-for="r in results" :key="r.file_id"
                :result="r"
                :downloading="downloading === r.file_id"
                :selectable="results.length >= 2"
                :selected="compareSelection.some(s => s.file_id === r.file_id)"
                @download="downloadItem($event)"
                @select="toggleCompareSelect(r)"
              />
            </div>
            <SubDesyncBanner v-if="lastDlResult" :desync="lastDlResult.desync" :encoding="lastDlResult.encoding" />

            <!-- Correction decalage -->
            <div v-if="lastDlResult && lastDlResult.desync && lastDlResult.desync.desynced" class="si-shift-bar">
              <span class="si-shift-label">{{ $t('subtitles.shiftLabel') }}</span>
              <input v-model.number="shiftMs" type="number" step="500" class="si-shift-input" placeholder="ms" />
              <button class="si-shift-btn" :disabled="!shiftMs" @click="doShift">
                {{ $t('subtitles.shiftApply') }}
              </button>
              <button class="si-shift-auto" :title="$t('subtitles.shiftAuto')" @click="shiftMs = Math.round(-lastDlResult.desync.delta_sec * 1000)">
                Auto ({{ lastDlResult.desync.delta_sec > 0 ? '-' : '+' }}{{ Math.abs(Math.round(lastDlResult.desync.delta_sec * 1000)) }}ms)
              </button>
            </div>
          </div>
        </div>
        <SubComparatorModal v-if="showComparator" :visible="showComparator" :file-a="compareSelection[0] || null" :file-b="compareSelection[1] || null" @close="showComparator = false" />
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import SubOsResultRow from './SubOsResultRow.vue'
import SubDesyncBanner from './SubDesyncBanner.vue'
import SubComparatorModal from './SubComparatorModal.vue'
import { useSubItemOverlay } from './useSubItemOverlay.js'
import { Trash2, X } from 'lucide-vue-next'

import '@/assets/styles/subtitles/item-overlay.css'

const props = defineProps({
  visible: Boolean,
  item: { type: Object, default: null },
})
const emit = defineEmits(['close', 'downloaded'])

const {
  subs, audio, results, searching, downloading, lastDlResult, shiftMs,
  removing, removeSelection, compareSelection, showComparator,
  toggleCompareSelect, searchItem, downloadItem, deleteSub,
  toggleRemove, batchRemove, doShift, formatChannels,
} = useSubItemOverlay(props, emit)
</script>
