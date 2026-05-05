<template>
  <div class="cinema-subs mk-page-root">
    <div class="sub-tabs-header">
      <SubHeader @edit-profiles="showProfileModal = true" />
    </div>

    <SubLibraryTab
      v-show="tab === 'library'"
      ref="libraryRef"
      @update-missing="missingCount = $event"
      @audit="showAuditPanel = true"
    />
    <SubSearchTab v-show="tab === 'search'" ref="searchRef" :initial-query="initialSearch" />
    <SubHistoryTab v-show="tab === 'history'" />
    <SubStatisticsTab v-show="tab === 'statistics'" ref="statsRef" />

    <SubProfileModal v-if="showProfileModal" @close="showProfileModal = false" />
    <SubAuditPanel :visible="showAuditPanel" @close="showAuditPanel = false" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSubtitles } from '@/composables/useSubtitles'
import { useTabSync } from '@/composables/useTabSync'

import SubHeader from '@/components/subtitles/SubHeader.vue'
import SubLibraryTab from '@/components/subtitles/SubLibraryTab.vue'
import SubSearchTab from '@/components/subtitles/SubSearchTab.vue'
import SubHistoryTab from '@/components/subtitles/SubHistoryTab.vue'
import SubStatisticsTab from '@/components/subtitles/SubStatisticsTab.vue'
import SubProfileModal from '@/components/subtitles/SubProfileModal.vue'
import SubAuditPanel from '@/components/subtitles/SubAuditPanel.vue'

const route = useRoute()
const { init } = useSubtitles()

const tab = useTabSync(['library', 'search', 'history', 'statistics'], 'library')
const missingCount = ref(0)
const showProfileModal = ref(false)
const showAuditPanel = ref(false)
const initialSearch = ref('')

const libraryRef = ref(null)
const searchRef = ref(null)
const statsRef = ref(null)

watch(tab, v => {
  if (v === 'statistics' && statsRef.value) {
    statsRef.value.loadStats()
  }
})

onMounted(() => {
  init()
  if (route.query.search) {
    initialSearch.value = route.query.search
    tab.value = 'search'
  }
})
</script>

<style scoped>
.cinema-subs {
  padding: 12px 24px 24px;
  position: relative;
  min-height: 100%;
  overflow: hidden;
}

.sub-tabs-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.sub-tabs-header > :first-child {
  flex: 1;
}
</style>
