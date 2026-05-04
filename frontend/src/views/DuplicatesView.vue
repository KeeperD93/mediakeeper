<template>
  <div class="cinema-duplicates mk-page-root">
    <div class="doub-content">
      <!-- ══════ TAB: Duplicates ══════ -->
      <div v-show="activeTab === 'duplicates'" class="tab-panel">
        <!-- KPIs -->
        <div class="doub-kpis">
          <div class="doub-kpi glass-kpi">
            <span class="kpi-val doub-kpi-err">{{ activeDuplicates.length }}</span>
            <span class="kpi-label">{{ $t('duplicates.activeDuplicates') }}</span>
          </div>
          <div class="doub-kpi glass-kpi">
            <span class="kpi-val doub-kpi-warn">{{ totalReclaimable }}</span>
            <span class="kpi-label">{{ $t('duplicates.reclaimableSpace') }}</span>
          </div>
          <div class="doub-kpi glass-kpi">
            <span class="kpi-val doub-kpi-ok">{{ historyStats.total_deleted }}</span>
            <span class="kpi-label">{{ $t('duplicates.cleanedFiles') }}</span>
          </div>
          <div class="doub-kpi glass-kpi">
            <span class="kpi-val doub-kpi-info">
              {{ formatBytes(historyStats.total_bytes_freed) }}
            </span>
            <span class="kpi-label">{{ $t('duplicates.totalFreedSpace') }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="doub-header">
          <div class="doub-actions">
            <button class="doub-btn doub-btn-secondary" :disabled="scanning" @click="scanEmby">
              <RefreshCw class="ic" />
              {{ $t('duplicates.scanEmby') }}
            </button>
            <button class="doub-btn doub-btn-primary" :disabled="refreshing" @click="refresh">
              <span v-if="refreshing" class="mk-spin mk-spin-14" />
              <Search v-else class="ic" />
              {{ refreshing ? $t('duplicates.detecting') : $t('duplicates.detect') }}
            </button>
            <button
              v-if="activeDuplicates.length && rules.length"
              class="doub-btn doub-btn-accent"
              @click="applyRules"
            >
              <Zap class="ic" />
              {{ $t('duplicates.applyRules', { count: rulesMatchCount }) }}
            </button>
          </div>
        </div>

        <!-- Loading / Empty -->
        <div v-if="loading && !duplicates.length" class="doub-grid">
          <div v-for="i in 3" :key="'sk' + i" class="doub-card doub-skeleton">
            <div class="skel-poster" />
            <div class="skel-body">
              <div class="skel-line skel-title" />
              <div class="skel-line skel-sub" />
              <div class="skel-source" />
            </div>
          </div>
        </div>
        <MkEmptyState
          v-else-if="!loading && !activeDuplicates.length"
          :icon="CircleCheck"
          :title="$t('duplicates.noduplicates')"
          :sub="$t('duplicates.libraryClean')"
        />

        <!-- Cards -->
        <div v-else class="doub-grid">
          <div v-for="item in activeDuplicates" :key="item.id" class="doub-card">
            <div class="doub-poster">
              <img
                v-if="item.poster"
                :src="item.poster"
                class="doub-poster-img"
                @error="e => (e.target.style.display = 'none')"
              />
              <div v-else class="doub-poster-ph"><Film class="w-8 h-8" :stroke-width="1.5" /></div>
              <span v-if="item.year" class="doub-year">{{ item.year }}</span>
            </div>
            <div class="doub-info">
              <div class="doub-info-header">
                <div>
                  <h3 class="doub-title">{{ item.title }}</h3>
                  <p class="doub-versions">
                    {{ item.sources.length }} {{ $t('duplicates.versions') }} ·
                    {{ reclaimableFor(item) }} {{ $t('duplicates.reclaimable') }}
                  </p>
                </div>
                <div class="doub-info-btns">
                  <button
                    v-if="bestSource(item)"
                    class="doub-suggest-btn"
                    :title="$t('duplicates.keepBest')"
                    @click="keepSource(item, bestSource(item))"
                  >
                    <Zap class="ic-sm" />
                    {{ $t('duplicates.keepBestBtn') }}
                  </button>
                  <button
                    class="doub-compare-btn"
                    :class="{ active: compareOpen === item.id }"
                    @click="toggleCompare(item.id)"
                  >
                    <Files class="ic-sm" />
                    {{ $t('duplicates.compare') }}
                  </button>
                  <button class="doub-ignore-btn" @click="ignoreDuplicate(item)">
                    <EyeOff class="ic-sm" />
                    {{ $t('duplicates.ignore') }}
                  </button>
                </div>
              </div>

              <!-- Compare panel -->
              <div v-if="compareOpen === item.id" class="doub-compare">
                <table class="cmp-table">
                  <thead>
                    <tr>
                      <th>{{ $t('duplicates.file') }}</th>
                      <th>{{ $t('duplicates.resolution') }}</th>
                      <th>{{ $t('duplicates.codec') }}</th>
                      <th>{{ $t('duplicates.size') }}</th>
                      <th>{{ $t('duplicates.score') }}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(src, si) in item.sources"
                      :key="si"
                      :class="{ 'cmp-best': isBest(item, src) }"
                    >
                      <td class="cmp-file" :title="src.name">{{ src.name }}</td>
                      <td>{{ src.resolution }}</td>
                      <td>{{ src.codec }}</td>
                      <td>{{ src.size_label }}</td>
                      <td>
                        <span class="cmp-score" :style="{ color: scoreColor(srcScore(src)) }">
                          {{ srcScore(src) }}
                        </span>
                      </td>
                      <td class="cmp-actions">
                        <button class="doub-keep-btn" @click="keepSource(item, src)">
                          {{ $t('duplicates.keep') }}
                        </button>
                        <button class="doub-delete-btn" @click="deleteSource(item, src)">
                          {{ $t('duplicates.delete') }}
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Sources (default view) -->
              <div v-else class="doub-sources">
                <div
                  v-for="(src, si) in item.sources"
                  :key="si"
                  class="doub-source"
                  :class="{ 'doub-source-best': isBest(item, src) }"
                >
                  <div class="doub-source-info">
                    <p class="doub-filename" :title="src.name">{{ src.name }}</p>
                    <div class="doub-tags">
                      <span class="doub-tag">{{ src.resolution || 'N/A' }}</span>
                      <span class="doub-tag">{{ src.codec || 'N/A' }}</span>
                      <span class="doub-tag">{{ src.size_label || '0 Mo' }}</span>
                      <span v-if="isBest(item, src)" class="doub-tag doub-tag-best">
                        ★ {{ $t('duplicates.best') }}
                      </span>
                    </div>
                  </div>
                  <div class="doub-source-acts">
                    <button class="doub-keep-btn" @click="keepSource(item, src)">
                      {{ $t('duplicates.keep') }}
                    </button>
                    <button class="doub-delete-btn" @click="deleteSource(item, src)">
                      {{ $t('duplicates.deleteFile') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════ TAB: Ignored ══════ -->
      <div v-show="activeTab === 'ignored'" class="tab-panel">
        <MkEmptyState
          v-if="!ignoredItems.length"
          :title="$t('duplicates.noIgnored')"
          :sub="$t('duplicates.ignoredHint')"
        />
        <div v-else class="doub-grid">
          <div v-for="ig in ignoredItems" :key="ig.key" class="doub-card doub-card-ignored">
            <div class="doub-info doub-info-flex">
              <div class="doub-info-header">
                <div>
                  <h3 class="doub-title">{{ ig.title || ig.key }}</h3>
                  <p v-if="ig.ignored_at" class="doub-versions">
                    {{ $t('duplicates.ignoredOn', { date: fmtDate(ig.ignored_at) }) }}
                  </p>
                </div>
                <button class="doub-restore-btn" @click="restoreDuplicate(ig.key)">
                  <RefreshCw class="ic-sm" />
                  {{ $t('common.restore') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════ TAB: History ══════ -->
      <div v-show="activeTab === 'history'" class="tab-panel">
        <MkEmptyState
          v-if="!history.length"
          :title="$t('duplicates.noHistory')"
          :sub="$t('duplicates.historyHint')"
        />
        <div v-else class="doub-history">
          <div v-for="h in history" :key="h.id" class="hist-row">
            <div class="hist-icon" :class="h.action === 'deleted' ? 'hist-del' : 'hist-keep'">
              <Trash2 v-if="h.action === 'deleted'" class="ic-sm" />
              <Check v-else class="ic-sm" />
            </div>
            <div class="hist-info">
              <div class="hist-title">{{ h.title || $t('common.unknown') }}</div>
              <div class="hist-file">{{ h.filename || '' }}</div>
            </div>
            <div class="hist-meta">
              <span class="hist-size">{{ formatBytes(h.size_bytes) }}</span>
              <span class="hist-date">{{ fmtDate(h.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════ TAB: Rules ══════ -->
      <div v-show="activeTab === 'rules'" class="tab-panel">
        <p class="rules-desc">{{ $t('duplicates.rulesDescription') }}</p>
        <div class="rules-list">
          <div v-for="(rule, ri) in rules" :key="ri" class="rule-row">
            <select v-model="rule.field" class="rule-sel">
              <option value="resolution">{{ $t('duplicates.ruleResolution') }}</option>
              <option value="codec">{{ $t('duplicates.ruleCodec') }}</option>
              <option value="keep_largest">{{ $t('duplicates.ruleKeepLargest') }}</option>
              <option value="keep_smallest">{{ $t('duplicates.ruleKeepSmallest') }}</option>
            </select>
            <input
              v-if="rule.field === 'resolution'"
              v-model="rule.value"
              class="rule-input"
              placeholder="ex: 1080p"
            />
            <input
              v-else-if="rule.field === 'codec'"
              v-model="rule.value"
              class="rule-input"
              placeholder="ex: HEVC"
            />
            <span v-else class="rule-auto">{{ $t('duplicates.automatic') }}</span>
            <button class="rule-del" @click="(rules.splice(ri, 1), saveRules())">✕</button>
          </div>
        </div>
        <button
          class="doub-btn doub-btn-secondary doub-btn-spaced"
          @click="(rules.push({ field: 'keep_largest', value: '' }), saveRules())"
        >
          {{ $t('duplicates.addRule') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDuplicates } from '@/composables/useDuplicates'
import { useTabSync } from '@/composables/useTabSync'
import {
  CircleCheck,
  Check,
  EyeOff,
  Film,
  Files,
  RefreshCw,
  Search,
  Trash2,
  Zap,
} from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import '@/assets/styles/duplicates-view.css'

const {
  duplicates,
  loading,
  refreshing,
  scanning,
  ignoredItems,
  history,
  historyStats,
  rules,
  activeDuplicates,
  totalReclaimable,
  rulesMatchCount,
  saveRules,
  srcScore,
  bestSource,
  isBest,
  scoreColor,
  formatBytes,
  fmtDate,
  reclaimableFor,
  applyRules,
  loadDuplicates,
  loadIgnored,
  loadHistory,
  loadHistoryStats,
  ignoreDuplicate,
  restoreDuplicate,
  deleteSource,
  keepSource,
  scanEmby,
  refresh,
} = useDuplicates()

const activeTab = useTabSync(['duplicates', 'ignored', 'history', 'rules'], 'duplicates')
const compareOpen = ref(null)
function toggleCompare(id) {
  compareOpen.value = compareOpen.value === id ? null : id
}

onMounted(async () => {
  await Promise.all([loadDuplicates(), loadIgnored(), loadHistory(), loadHistoryStats()])
})
</script>
