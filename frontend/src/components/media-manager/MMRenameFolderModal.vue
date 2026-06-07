<template>
  <div
    class="mr-overlay"
    :class="{ show: modalRenameFolderShow }"
    :inert="!modalRenameFolderShow"
    @click.self="close"
  >
    <div ref="panelRef" class="mr-modal" role="dialog" aria-modal="true" :aria-labelledby="titleId">
      <header class="mr-header">
        <div class="mr-header-title">
          <Pencil :size="16" />
          <h3 :id="titleId">{{ $t('mediaManager.renameFolderTitle') }}</h3>
          <span v-if="categoryLabel" class="mr-chip">
            <Folder :size="11" />
            {{ categoryLabel }}
          </span>
        </div>
        <button ref="closeBtnRef" class="mr-close" :title="$t('common.close')" @click="close">
          <X :size="14" />
        </button>
      </header>

      <div class="mr-body">
        <div v-if="parentSegments.length" class="mr-bc">
          <span class="mr-bc-root">
            <Folder :size="11" />
            {{ categoryLabel }}
          </span>
          <template v-for="(seg, i) in parentSegments" :key="i">
            <ChevronRight :size="11" class="mr-bc-sep" />
            <span class="mr-bc-seg">{{ seg }}</span>
          </template>
        </div>

        <div>
          <div class="mr-section-label">{{ $t('mediaManager.currentFolder') }}</div>
          <div class="mr-current-card">
            <span class="mr-current-icon"><Folder :size="16" /></span>
            <span class="mr-current-name" :title="renameFolderCurrent">
              {{ renameFolderCurrent }}
            </span>
          </div>
        </div>

        <div>
          <div class="mr-section-label">{{ $t('mediaManager.newFolderName') }}</div>
          <div class="mr-input-wrap">
            <Pencil :size="12" />
            <input
              ref="inputRef"
              v-model="renameFolderValue"
              :placeholder="$t('mediaManager.newNamePlaceholder')"
              @keydown.enter="onEnter"
            />
          </div>
        </div>
      </div>

      <footer class="mr-footer">
        <div class="mr-preview">
          <span class="mr-preview-label">{{ $t('mediaManager.newPath') }}</span>
          <span
            class="mr-preview-path"
            :class="{ empty: !trimmedValue, unchanged: !hasChange && trimmedValue }"
          >
            {{ previewText }}
          </span>
        </div>
        <div class="mr-actions">
          <button class="mr-btn-ghost" @click="close">{{ $t('common.close') }}</button>
          <button class="mr-btn-primary" :disabled="!hasChange" @click="execRenameFolder">
            <Check :size="13" />
            {{ $t('mediaManager.rename') }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useMediaManager, CATS } from '@/composables/useMediaManager'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { Check, ChevronRight, Folder, Pencil, X } from 'lucide-vue-next'
import '@/assets/styles/rename-folder-modal.css'

const {
  modalRenameFolderShow,
  renameFolderCurrent,
  renameFolderValue,
  activeCat,
  subPath,
  execRenameFolder,
} = useMediaManager()

const inputRef = ref(null)
const panelRef = ref(null)
const closeBtnRef = ref(null)

const categoryLabel = computed(() => CATS.value.find(c => c.key === activeCat.value)?.label || '')

const parentSegments = computed(() => {
  const all = (subPath.value || '').split('/').filter(Boolean)
  return all.slice(0, -1)
})

const trimmedValue = computed(() => (renameFolderValue.value || '').trim())
const hasChange = computed(
  () => trimmedValue.value && trimmedValue.value !== renameFolderCurrent.value,
)

const previewText = computed(() => {
  if (!trimmedValue.value) return '—'
  const parent = parentSegments.value.join('/')
  return parent ? `${parent}/${trimmedValue.value}` : trimmedValue.value
})

function close() {
  modalRenameFolderShow.value = false
}
function onEnter() {
  if (hasChange.value) execRenameFolder()
}

const titleId = useId()
useFocusTrap({
  active: modalRenameFolderShow,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})

watch(modalRenameFolderShow, async v => {
  if (!v) return
  await nextTick()
  inputRef.value?.focus()
  inputRef.value?.select()
})
</script>
