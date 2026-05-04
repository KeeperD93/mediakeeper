<template>
  <!-- ── MODAL HISTORIQUE RENOMMAGE ── -->
  <div
    class="mm-overlay"
    :class="{ show: modelValue }"
    @click.self="$emit('update:modelValue', false)"
  >
    <div class="mm-modal mm-modal-560">
      <h3>
        <Clock />
        {{ $t('mediaManager.renameHistoryTitle') }}
      </h3>
      <div class="mm-modal-body mm-hist-body">
        <div v-if="!renameHistory.length" class="mm-state mm-state-empty">
          <span>{{ $t('mediaManager.noRenameHistory') }}</span>
        </div>
        <div v-for="(entry, hi) in renameHistoryPage" :key="entry.timestamp" class="mm-hist-entry">
          <div class="mm-hist-header">
            <span class="mm-hist-title">{{ entry.tmdbTitle || 'Renommage' }}</span>
            <span class="mm-hist-meta">
              {{ entry.items.length }} fichier(s) ·
              {{
                new Date(entry.timestamp).toLocaleDateString(undefined, {
                  day: '2-digit',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })
              }}
            </span>
            <button
              class="mm-btn-sm mm-btn-warn-light"
              :title="$t('common.cancel')"
              @click="undoRename(histPageOffset + hi)"
            >
              <RefreshCw :size="11" />
              Undo
            </button>
          </div>
          <div v-for="item in entry.items.slice(0, 3)" :key="item.oldName" class="mm-hist-item">
            <span class="mm-hist-old">
              {{ item.oldName.length > 40 ? '…' + item.oldName.slice(-38) : item.oldName }}
            </span>
            <span class="mm-hist-new">
              → {{ item.newName.length > 40 ? item.newName.slice(0, 38) + '…' : item.newName }}
            </span>
          </div>
          <div v-if="entry.items.length > 3" class="mm-hist-more">
            + {{ entry.items.length - 3 }} autres…
          </div>
        </div>
      </div>
      <div v-if="histTotalPages > 1" class="mm-hist-pages">
        <button class="mm-btn-sm" :disabled="histPage === 0" @click="histPage--">‹</button>
        <span class="mm-page-counter">{{ histPage + 1 }} / {{ histTotalPages }}</span>
        <button class="mm-btn-sm" :disabled="histPage >= histTotalPages - 1" @click="histPage++">
          ›
        </button>
      </div>
      <div class="mm-modal-footer">
        <button
          v-if="renameHistory.length"
          class="mm-btn-sm mm-btn-clear"
          @click="clearRenameHistory"
        >
          {{ $t('mediaManager.clearHistory') }}
        </button>
        <button class="mm-btn-sm" @click="$emit('update:modelValue', false)">
          {{ $t('common.close') }}
        </button>
      </div>
    </div>
  </div>

  <!-- ── MOVE HISTORY MODAL ── -->
  <div
    class="mm-overlay"
    :class="{ show: showMoveHistoryModal }"
    @click.self="showMoveHistoryModal = false"
  >
    <div class="mm-modal mm-modal-560">
      <h3>
        <ArrowLeftRight />
        {{ $t('mediaManager.cancelMoves') }}
      </h3>
      <div class="mm-modal-body mm-hist-body">
        <div v-if="!moveHistory.length" class="mm-state mm-state-empty">
          <span>{{ $t('mediaManager.noMoveHistory') }}</span>
        </div>
        <div v-for="(entry, mi) in moveHistoryPage" :key="entry.timestamp" class="mm-hist-entry">
          <div class="mm-hist-header">
            <span class="mm-hist-title">
              {{ $t('mediaManager.filesMovedCount', { count: entry.items.length }) }}
            </span>
            <span class="mm-hist-meta">
              {{
                new Date(entry.timestamp).toLocaleDateString(undefined, {
                  day: '2-digit',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })
              }}
            </span>
            <button
              class="mm-btn-sm mm-btn-warn-light"
              :title="$t('common.cancel')"
              @click="undoMove(movePageOffset + mi)"
            >
              <RefreshCw :size="11" />
              {{ $t('common.cancel') }}
            </button>
          </div>
          <div v-for="f in entry.items.slice(0, 3)" :key="f.newPath" class="mm-hist-item">
            <span class="mm-hist-old">{{ f.name }}</span>
            <span class="mm-hist-new">→ {{ entry.dest }}</span>
          </div>
          <div v-if="entry.items.length > 3" class="mm-hist-more">
            + {{ entry.items.length - 3 }} autres…
          </div>
        </div>
      </div>
      <div v-if="moveTotalPages > 1" class="mm-hist-pages">
        <button class="mm-btn-sm" :disabled="movePage === 0" @click="movePage--">‹</button>
        <span class="mm-page-counter">{{ movePage + 1 }} / {{ moveTotalPages }}</span>
        <button class="mm-btn-sm" :disabled="movePage >= moveTotalPages - 1" @click="movePage++">
          ›
        </button>
      </div>
      <div class="mm-modal-footer">
        <button v-if="moveHistory.length" class="mm-btn-sm mm-btn-clear" @click="clearMoveHistory">
          {{ $t('mediaManager.clearHistory') }}
        </button>
        <button class="mm-btn-sm" @click="showMoveHistoryModal = false">
          {{ $t('common.close') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMediaManager } from '@/composables/useMediaManager'
import { ArrowLeftRight, Clock, RefreshCw } from 'lucide-vue-next'

defineProps({ modelValue: { type: Boolean, default: false } })
defineEmits(['update:modelValue'])

const {
  renameHistory,
  moveHistory,
  showMoveHistoryModal,
  undoRename,
  clearRenameHistory,
  undoMove,
  clearMoveHistory,
} = useMediaManager()

const HIST_PAGE_SIZE = 5
const histPage = ref(0)
const histTotalPages = computed(() =>
  Math.max(1, Math.ceil(renameHistory.value.length / HIST_PAGE_SIZE)),
)
const histPageOffset = computed(() => histPage.value * HIST_PAGE_SIZE)
const renameHistoryPage = computed(() =>
  renameHistory.value.slice(histPageOffset.value, histPageOffset.value + HIST_PAGE_SIZE),
)

const MOVE_PAGE_SIZE = 5
const movePage = ref(0)
const moveTotalPages = computed(() =>
  Math.max(1, Math.ceil(moveHistory.value.length / MOVE_PAGE_SIZE)),
)
const movePageOffset = computed(() => movePage.value * MOVE_PAGE_SIZE)
const moveHistoryPage = computed(() =>
  moveHistory.value.slice(movePageOffset.value, movePageOffset.value + MOVE_PAGE_SIZE),
)
</script>

<style scoped>
/* Modal size: history modals are 560px wide */
.mm-modal-560 {
  width: 560px;
}
/* Shared scroll body for history lists */
.mm-hist-body {
  max-height: 380px;
}
/* Empty-state centred padding */
.mm-state-empty {
  padding: 1rem;
}
/* Old/new file name colours inside a history row */
.mm-hist-old {
  color: var(--text-muted);
}
.mm-hist-new {
  color: var(--mm-green);
}
/* "+N autres…" line under truncated list */
.mm-hist-more {
  font-size: var(--text-3xs);
  color: var(--text-muted);
  padding-left: 0.5rem;
}
/* Page counter between pagination buttons */
.mm-page-counter {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
/* Clear-history button (destructive look) */
.mm-btn-clear {
  color: var(--mm-red);
}
</style>
