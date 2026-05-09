<template>
  <div class="mv-overlay" :class="{ show: modalMoveShow }" @click.self="closeMoveModal">
    <div ref="panelRef" class="mv-modal" role="dialog" aria-modal="true">
      <header class="mv-header">
        <div class="mv-header-title">
          <ArrowLeftRight :size="16" />
          <h3>{{ $t('mediaManager.moveTo') }}</h3>
          <span v-if="moveSourcesCount" class="mv-chip">
            <Files :size="11" />
            {{ $t('mediaManager.movingNFiles', { count: moveSourcesCount }, moveSourcesCount) }}
          </span>
        </div>
        <button ref="closeBtnRef" class="mv-close" :title="$t('common.close')" @click="closeMoveModal">
          <X :size="14" />
        </button>
      </header>

      <div class="mv-layout">
        <aside class="mv-sidebar">
          <div class="mv-sidebar-label">{{ $t('mediaManager.categories') }}</div>
          <button
            v-for="c in CATS"
            :key="c.key"
            class="mv-cat-row"
            :class="{ active: moveCat === c.key }"
            @click="moveChangeCat(c.key)"
          >
            <Folder :size="14" />
            <span class="mv-cat-label">{{ c.label }}</span>
          </button>
        </aside>

        <section class="mv-content">
          <div class="mv-bc">
            <span class="mv-bc-root" @click="moveNavRoot">
              <Folder :size="11" />
              {{ CATS.find(c => c.key === moveCat)?.label }}
            </span>
            <template v-for="(seg, i) in moveBreadcrumbs" :key="i">
              <ChevronRight :size="11" class="mv-bc-sep" />
              <span class="mv-bc-seg" @click="moveNavTo(i)">{{ seg }}</span>
            </template>
          </div>

          <div class="mv-tools">
            <div class="mv-tool-input">
              <Search :size="12" />
              <input v-model="moveSearchQ" :placeholder="$t('mediaManager.searchFolder')" />
            </div>
            <div class="mv-tool-input mv-tool-input--mono">
              <Link2 :size="12" />
              <input
                v-model="moveManualPath"
                :placeholder="$t('mediaManager.manualPathPlaceholder')"
                @keydown.enter="applyManualPath"
              />
            </div>
            <button
              class="mv-tool-go"
              :title="$t('mediaManager.manualPathGo')"
              @click="applyManualPath"
            >
              <ArrowRight :size="12" />
            </button>
          </div>

          <div class="mv-list">
            <div v-if="moveLoading" class="mv-state">
              <MkSpinner size="sm" />
              <span>{{ $t('mediaManager.loading') }}</span>
            </div>

            <button
              class="mv-card mv-card-here"
              :class="{ selected: moveSelectedPath === currentFolderPath }"
              @click="movePickCurrent"
            >
              <span class="mv-card-icon"><Target :size="18" /></span>
              <span class="mv-card-body">
                <span class="mv-card-name">{{ $t('mediaManager.dropHereTitle') }}</span>
                <span class="mv-card-hint">
                  {{ movePath || CATS.find(c => c.key === moveCat)?.label }}
                </span>
              </span>
              <span class="mv-card-cta">
                <Check :size="13" />
                {{ $t('mediaManager.selectThisFolder') }}
              </span>
            </button>

            <div class="mv-card mv-card-create">
              <span class="mv-card-icon"><FolderPlus :size="18" /></span>
              <input
                v-model="newFolderName"
                class="mv-card-create-input"
                :placeholder="$t('mediaManager.createFolderPlaceholder')"
                :disabled="creatingFolder"
                @keydown.enter="onConfirmCreateFolder"
              />
              <button
                class="mv-card-action mv-card-action--always"
                :title="$t('mediaManager.createFolderHere')"
                :disabled="!newFolderName.trim() || creatingFolder"
                @click.stop="onConfirmCreateFolder"
              >
                <Check :size="13" />
              </button>
            </div>

            <div
              v-if="suggestedMoveFolder"
              class="mv-card mv-card-suggested"
              role="button"
              tabindex="0"
              :class="{
                'mv-card-suggested--approx': !suggestedMoveFolder.exact,
                selected: moveSelectedPath === suggestedAbsPath,
              }"
              @click="moveEnterFolder(movePath, suggestedMoveFolder.folder.name)"
              @keydown.enter="moveEnterFolder(movePath, suggestedMoveFolder.folder.name)"
              @keydown.space.prevent="moveEnterFolder(movePath, suggestedMoveFolder.folder.name)"
            >
              <span class="mv-card-icon"><Sparkles :size="16" /></span>
              <span class="mv-card-body">
                <span class="mv-card-name">{{ suggestedMoveFolder.folder.name }}</span>
                <span class="mv-card-hint">
                  {{
                    suggestedMoveFolder.exact
                      ? $t('mediaManager.suggestedMatchHint')
                      : $t('mediaManager.suggestedMatchApproxHint')
                  }}
                </span>
              </span>
              <button
                class="mv-card-action"
                :title="$t('mediaManager.selectThisFolder')"
                @click.stop="
                  movePickFolder(suggestedMoveFolder.folder.path, suggestedMoveFolder.folder.name)
                "
              >
                <Check :size="13" />
              </button>
            </div>

            <div
              v-if="recentMoveDestinations.length && !moveSearchQ && !movePath"
              class="mv-collapsible"
              :class="{ open: recentExpanded }"
            >
              <button class="mv-collapsible-header" @click="recentExpanded = !recentExpanded">
                <ChevronRight :size="12" class="mv-collapsible-chevron" />
                <span>{{ $t('mediaManager.recentDestinations') }}</span>
                <span class="mv-collapsible-count">{{ recentMoveDestinations.length }}</span>
              </button>
              <div v-if="recentExpanded" class="mv-collapsible-body">
                <button
                  v-for="dest in recentMoveDestinations"
                  :key="dest"
                  class="mv-card mv-card-recent"
                  :class="{ selected: moveSelectedPath === dest }"
                  @click="jumpToAbsolutePath(dest)"
                >
                  <span class="mv-card-icon"><History :size="16" /></span>
                  <span class="mv-card-body">
                    <span class="mv-card-name">{{ dest.split('/').slice(-2).join('/') }}</span>
                    <span class="mv-card-hint mv-card-hint--mono">{{ dest }}</span>
                  </span>
                </button>
              </div>
            </div>

            <div v-if="moveFoldersFiltered.length" class="mv-section-label">
              {{ $t('mediaManager.allFolders') }}
            </div>

            <div
              v-for="f in moveFoldersFiltered"
              :key="f.path"
              class="mv-card"
              role="button"
              tabindex="0"
              :class="{ selected: moveSelectedPath === folderAbsPath(f) }"
              @click="moveEnterFolder(movePath, f.name)"
              @keydown.enter="moveEnterFolder(movePath, f.name)"
              @keydown.space.prevent="moveEnterFolder(movePath, f.name)"
            >
              <span class="mv-card-icon"><Folder :size="16" /></span>
              <span class="mv-card-body">
                <span class="mv-card-name" :title="f.name">{{ f.name }}</span>
              </span>
              <button
                class="mv-card-action"
                :title="$t('mediaManager.selectThisFolder')"
                @click.stop="movePickFolder(f.path, f.name)"
              >
                <Check :size="13" />
              </button>
            </div>

            <div
              v-if="!moveLoading && !moveFoldersFiltered.length && !suggestedMoveFolder"
              class="mv-empty"
            >
              <FolderSearch :size="28" />
              <span>{{ $t('mediaManager.noFolders') }}</span>
            </div>
          </div>
        </section>
      </div>

      <footer class="mv-footer">
        <div class="mv-preview">
          <span class="mv-preview-label">{{ $t('mediaManager.destination') }}</span>
          <span class="mv-preview-path" :class="{ empty: !moveTargetPreview }">
            {{ moveTargetPreview || $t('mediaManager.noDestination') }}
          </span>
        </div>
        <div class="mv-actions">
          <button class="mv-btn-ghost" @click="closeMoveModal">{{ $t('common.cancel') }}</button>
          <button class="mv-btn-primary" :disabled="!moveSelectedPath" @click="execMove">
            <Check :size="13" />
            {{ $t('mediaManager.moveHereCta') }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import { useFocusTrap } from '@/composables/useFocusTrap'
import {
  ArrowLeftRight,
  ArrowRight,
  Check,
  ChevronRight,
  Files,
  Folder,
  FolderPlus,
  FolderSearch,
  History,
  Link2,
  Search,
  Sparkles,
  Target,
  X,
} from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'
import '@/assets/styles/move-modal.css'

const {
  modalMoveShow,
  moveCat,
  movePath,
  moveSearchQ,
  moveManualPath,
  moveSelectedPath,
  moveLoading,
  moveBreadcrumbs,
  moveFoldersFiltered,
  suggestedMoveFolder,
  moveTargetPreview,
  recentMoveDestinations,
  moveSourcesCount,
  closeMoveModal,
  execMove,
  moveChangeCat,
  moveEnterFolder,
  moveNavTo,
  moveNavRoot,
  movePickFolder,
  movePickCurrent,
  createMoveFolder,
  jumpToAbsolutePath,
  applyManualPath,
} = useMediaManager()

const recentExpanded = ref(false)
const newFolderName = ref('')
const creatingFolder = ref(false)
const panelRef = ref(null)
const closeBtnRef = ref(null)

async function onConfirmCreateFolder() {
  if (!newFolderName.value.trim() || creatingFolder.value) return
  creatingFolder.value = true
  const ok = await createMoveFolder(newFolderName.value)
  creatingFolder.value = false
  if (ok) newFolderName.value = ''
}

const currentFolderPath = computed(() => {
  if (movePath.value) return movePath.value
  const cat = CATS.value.find(c => c.key === moveCat.value)
  return cat?.path || ''
})

const suggestedAbsPath = computed(() => {
  const s = suggestedMoveFolder.value
  if (!s?.folder) return ''
  return movePath.value ? `${movePath.value}/${s.folder.name}` : s.folder.name
})

function folderAbsPath(f) {
  return movePath.value ? `${movePath.value}/${f.name}` : f.name
}

useFocusTrap({
  active: modalMoveShow,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: closeMoveModal,
})
</script>
