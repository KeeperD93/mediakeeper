<template>
  <div class="cinema-duplicates mk-page-root">
    <div class="doub-content">
      <!-- ══════ TAB: Duplicates ══════ -->
      <div v-show="activeTab === 'duplicates'" class="tab-panel">
        <DupKpiBar
          :active-count="activeDuplicates.length"
          :reclaimable="totalReclaimable"
          :deleted-count="historyStats.total_deleted"
          :freed-bytes="historyStats.total_bytes_freed"
        />

        <!-- Actions -->
        <div class="doub-header">
          <div class="doub-actions">
            <span v-if="lastDetection" class="doub-last-detection">
              {{ $t('duplicates.lastDetection') }} {{ formatAgo(lastDetection) }}
            </span>
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
          <DupCard
            v-for="item in activeDuplicates"
            :key="item.id"
            :item="item"
            :is-compare-open="compareOpen === item.id"
            @keep="keepSource"
            @delete="deleteSource"
            @ignore="ignoreDuplicate"
            @toggle-compare="toggleCompare"
          />
        </div>
      </div>

      <!-- ══════ TAB: Ignored ══════ -->
      <div v-show="activeTab === 'ignored'" class="tab-panel">
        <DupIgnoredView :items="ignoredItems" @restore="onRestoreKeys" />
      </div>

      <!-- ══════ TAB: History ══════ -->
      <div v-show="activeTab === 'history'" class="tab-panel">
        <DupHistoryList
          :history="history"
          :has-more="historyHasMore"
          :loading-more="loadingMoreHistory"
          @load-more="loadHistory(true)"
        />
      </div>

      <!-- ══════ TAB: Rules ══════ -->
      <div v-show="activeTab === 'rules'" class="tab-panel">
        <DupRulesPanel v-model="rules" @save="saveRules" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'DuplicatesView' })
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDuplicates } from '@/composables/useDuplicates'
import { useTabSync } from '@/composables/useTabSync'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
import { CircleCheck, Search, Zap } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import DupIgnoredView from '@/components/duplicates/DupIgnoredView.vue'
import DupKpiBar from '@/components/duplicates/DupKpiBar.vue'
import DupCard from '@/components/duplicates/DupCard.vue'
import DupHistoryList from '@/components/duplicates/DupHistoryList.vue'
import DupRulesPanel from '@/components/duplicates/DupRulesPanel.vue'
import { formatAgo as formatAgoUtil } from '@/utils/formatAgo'
import '@/assets/styles/duplicates-view.css'

const { t } = useI18n()
const formatAgo = input => formatAgoUtil(input, t)

const {
  duplicates,
  loading,
  refreshing,
  ignoredItems,
  history,
  historyHasMore,
  loadingMoreHistory,
  historyStats,
  rules,
  lastDetection,
  activeDuplicates,
  totalReclaimable,
  rulesMatchCount,
  saveRules,
  applyRules,
  loadDuplicates,
  loadIgnored,
  loadHistory,
  loadHistoryStats,
  ignoreDuplicate,
  restoreDuplicate,
  restoreDuplicates,
  deleteSource,
  keepSource,
  refresh,
} = useDuplicates()

const TAB_IDS = SIDEBAR_SUB_TABS['/duplicates'].map(tab => tab.id)
const activeTab = useTabSync(TAB_IDS, TAB_IDS[0])
const compareOpen = ref(null)
function toggleCompare(id) {
  compareOpen.value = compareOpen.value === id ? null : id
}

function onRestoreKeys(keys) {
  if (!keys?.length) return
  if (keys.length === 1) restoreDuplicate(keys[0])
  else restoreDuplicates(keys)
}

onMounted(async () => {
  await Promise.all([loadDuplicates(), loadIgnored(), loadHistory(), loadHistoryStats()])
})
</script>
