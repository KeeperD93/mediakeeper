<template>
  <!-- ── MODAL CONFIRMATION RENAME ── -->
  <div class="mm-overlay" :class="{show: modalConfirm.show}" @click.self="modalConfirm.show=false">
    <div class="mm-modal">
      <h3>
        <Pencil />
        {{ $t('mediaManager.confirmRenameTitle') }}
      </h3>
      <div class="mm-modal-body">
        <div v-for="n in modalConfirm.lines" :key="n.oldName" class="mm-confirm-line">
          <div class="mm-line-old">{{ n.oldName.length > 48 ? '…'+n.oldName.slice(-46) : n.oldName }}</div>
          <div class="mm-line-new">→ {{ n.name.length > 48 ? n.name.slice(0,46)+'…' : n.name }}</div>
        </div>
      </div>
      <div class="mm-modal-footer">
        <button class="mm-btn-sm" @click="modalConfirm.show=false">{{ $t('common.cancel') }}</button>
        <button class="mm-btn-sm mm-btn-success" @click="execRename">
          <Check />
          {{ $t('common.confirm') }}
        </button>
      </div>
    </div>
  </div>

  <!-- ── MOVE MODAL ── -->
  <MMMoveModal />

  <!-- ── FOLDERS / SEASONS MODAL ── -->
  <MMFolderModal />

  <!-- ── RENAME FOLDER MODAL ── -->
  <MMRenameFolderModal />

  <MMHistoryModals v-model="showHistoryModal" />
  <MMFileMetaModal />

  <!-- ── RENAME ERRORS MODAL ── -->
  <div class="mm-overlay" :class="{show: showRenameErrorsModal}" @click.self="clearRenameErrors">
    <div class="mm-modal mm-modal-580">
      <h3 class="mm-title-error">
        <TriangleAlert />
        {{ $t('mediaManager.renameErrorsTitle', { count: renameErrors?.length ?? 0 }, renameErrors?.length ?? 0) }}
      </h3>
      <div class="mm-modal-body mm-errors-body">
        <p class="mm-err-intro">{{ $t('mediaManager.checkPermissions') }}</p>
        <div v-for="(err, ei) in (renameErrors || [])" :key="ei" class="mm-err-entry">
          <div class="mm-err-row">
            <X :size="13" class="mm-err-icon" />
            <span class="mm-err-filename">{{ err.oldName }}</span>
          </div>
          <div class="mm-err-target">→ {{ err.newName }}</div>
          <div class="mm-err-reason">
            <Info :size="11" class="mm-ico-shrink" />
            {{ err.reason }}
          </div>
          <div class="mm-err-path">{{ err.path }}</div>
        </div>
      </div>
      <div class="mm-modal-footer">
        <button class="mm-btn-sm" @click="clearRenameErrors">{{ $t('common.close') }}</button>
      </div>
    </div>
  </div>

  <!-- ── MOVE CONFLICT MODAL ── -->
  <div class="mm-overlay" :class="{show: showMoveConflictModal}" @click.self="cancelMoveConflict">
    <div class="mm-modal mm-modal-500">
      <h3>
        <TriangleAlert class="mm-ico-warn" />
        {{ $t('mediaManager.conflictsTitle') }}
      </h3>
      <div class="mm-modal-body mm-conflict-body">
        <p class="mm-conflict-intro">{{ $t('mediaManager.filesAlreadyExist', { count: moveConflicts.length }) }}</p>
        <div v-for="c in moveConflicts" :key="c.name" class="mm-conflict-row">
          <span class="mm-conflict-name">{{ c.name }}</span>
          <span class="mm-conflict-size">{{ c.existing_size_label }}</span>
        </div>
      </div>
      <div class="mm-modal-footer mm-footer-gap">
        <button class="mm-btn-sm" @click="cancelMoveConflict">{{ $t('common.cancel') }}</button>
        <button class="mm-btn-sm" @click="execMoveWithOverwrite(false)">{{ $t('mediaManager.skipConflictsBtn') }}</button>
        <button class="mm-btn-sm mm-btn-warn-light" @click="execMoveWithOverwrite(true)">
          <CircleAlert class="mm-ico-11" />
          {{ $t('mediaManager.overwriteAll') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMediaManager } from '@/composables/useMediaManager'
import MMFileMetaModal from './MMFileMetaModal.vue'
import MMFolderModal from './MMFolderModal.vue'
import MMHistoryModals from './MMHistoryModals.vue'
import MMMoveModal from './MMMoveModal.vue'
import MMRenameFolderModal from './MMRenameFolderModal.vue'
import { Check, CircleAlert, Info, Pencil, TriangleAlert, X } from 'lucide-vue-next'

const {
  modalConfirm,
  renameErrors, showRenameErrorsModal,
  moveConflicts, showMoveConflictModal,
  execRename,
  clearRenameErrors, cancelMoveConflict, execMoveWithOverwrite,
} = useMediaManager()

const showHistoryModal = defineModel('showHistoryModal', { default: false })
</script>

<style scoped>
/* Modal sizing presets */
.mm-modal-500 { width: 500px; }
.mm-modal-580 { width: 580px; }

/* Confirm-rename line pair: old name + new name */
.mm-confirm-line { margin-bottom: .5rem; }
.mm-line-old { color: var(--text-muted); }
.mm-line-new { color: var(--mm-green); }

/* Errors modal */
.mm-title-error { color: var(--color-error); }
.mm-errors-body { max-height: 420px; }
.mm-err-intro { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: .7rem; }
.mm-err-icon { color: var(--color-error); flex-shrink: 0; }

/* Conflict modal */
.mm-conflict-body { max-height: 280px; }
.mm-conflict-intro { margin-bottom: .6rem; font-size: var(--text-sm); color: var(--text-secondary); }
.mm-footer-gap { gap: .4rem; }

/* Generic icon helpers */
.mm-ico-shrink { flex-shrink: 0; }
.mm-ico-warn { color: var(--color-warning); }
.mm-ico-11 { width: 11px; height: 11px; }
</style>
