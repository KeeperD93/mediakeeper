<template>
  <div class="cinema-mm mk-page-root">
    <div class="mm-content">
      <MMCatTabs />
      <div class="mm-main">
        <MMFileList ref="fileListComp" @scroll="onLeftScroll" />
        <MMTmdbPanel ref="tmdbPanelComp" @openConfig="openConfig" />
        <MMRenamePanel ref="renamePanelComp" @scroll="onRightScroll" />
      </div>
    </div>
    <MMModals v-model:show-history-modal="showHistoryModal" />
    <MMConfigPanels ref="configPanelsComp" v-model:show-config-panel="showConfigPanel" />
  </div>
</template>

<script setup>
import { ref, computed, provide, onMounted, onUnmounted, watch } from 'vue'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import MMCatTabs from '@/components/media-manager/MMCatTabs.vue'
import MMFileList from '@/components/media-manager/MMFileList.vue'
import MMTmdbPanel from '@/components/media-manager/MMTmdbPanel.vue'
import MMRenamePanel from '@/components/media-manager/MMRenamePanel.vue'
import MMModals from '@/components/media-manager/MMModals.vue'
import MMConfigPanels from '@/components/media-manager/MMConfigPanels.vue'

const {
  activeCat, checked, subPath, newNames, checkedFiles, checkedDirs,
  setCat, navRoot, navBack, loadFiles, deleteFile, deleteSelected, autoSearch, renameHistory,
  loadCategories, loadReleaseTags,
} = useMediaManager()

const showHistoryModal = ref(false)
provide('mmCtx', { showHistoryModal })

const fileListComp = ref(null)
const renamePanelComp = ref(null)
const tmdbPanelComp = ref(null)
const configPanelsComp = ref(null)
const showConfigPanel = ref(false)

function openConfig(tab = 'format') {
  configPanelsComp.value?.openConfigPanel(tab)
}

let _scrollSyncing = false
function onLeftScroll(scrollTop) {
  if (_scrollSyncing || !newNames.value.length) return
  const rightEl = renamePanelComp.value?.rightListRef
  if (rightEl) { _scrollSyncing = true; rightEl.scrollTop = scrollTop; _scrollSyncing = false }
}
function onRightScroll(scrollTop) {
  if (_scrollSyncing || !newNames.value.length) return
  const leftEl = fileListComp.value?.fileListRef
  if (leftEl) { _scrollSyncing = true; leftEl.scrollTop = scrollTop; _scrollSyncing = false }
}

function onKeyDown(e) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
  if (e.key === 'Delete') { const sel = [...checked.value]; if (sel.length === 1) deleteFile(sel[0]); else if (sel.length > 1) deleteSelected() }
  else if (e.key === 'Backspace') { if (subPath.value) { e.preventDefault(); navBack() } }
  else if (e.key === 'Escape') { if (subPath.value) navRoot(); else checked.value = new Set() }
  else if (e.key === 'ArrowLeft') { const idx = CATS.value.findIndex(c => c.key === activeCat.value); if (idx > 0) setCat(CATS.value[idx - 1].key) }
  else if (e.key === 'ArrowRight') { const idx = CATS.value.findIndex(c => c.key === activeCat.value); if (idx < CATS.value.length - 1) setCat(CATS.value[idx + 1].key) }
}

watch([checkedFiles, checkedDirs, subPath], () => {
  autoSearch(tmdbPanelComp.value?.tmdbQRef)
})

function purgeOldHistory() {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
  const before = renameHistory.value.length
  renameHistory.value = renameHistory.value.filter(e => e.timestamp > cutoff)
  if (renameHistory.value.length !== before) try { localStorage.setItem('mk_rename_history', JSON.stringify(renameHistory.value)) } catch { /* silent: localStorage quota/privacy mode → skip persist */ }
}

onMounted(async () => { await loadCategories(); loadFiles(); loadReleaseTags(); document.addEventListener('keydown', onKeyDown); purgeOldHistory() })
onUnmounted(() => { document.removeEventListener('keydown', onKeyDown) })
</script>
