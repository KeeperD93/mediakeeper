<template>
  <Teleport to="body">
    <div
      v-if="ctxMenu.show"
      class="mm-ctx-menu"
      :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
    >
      <button class="mm-ctx-item" @click="$emit('ctx-rename')">
        <Pencil :size="13" />
        {{ $t('mediaManager.ctxRename') }}
      </button>
      <button class="mm-ctx-item" @click="$emit('ctx-move')">
        <ArrowLeftRight :size="13" />
        {{ $t('mediaManager.ctxMove') }}
      </button>
      <button v-if="ctxMenu.file?.type === FILE_TYPE.FILE" class="mm-ctx-item" @click="$emit('ctx-info')">
        <Info :size="13" />
        {{ $t('mediaManager.ctxInfo') }}
      </button>
      <div class="mm-ctx-sep" />
      <button class="mm-ctx-item mm-ctx-danger" @click="$emit('ctx-delete')">
        <Trash2 :size="13" />
        {{ $t('mediaManager.ctxDelete') }}
      </button>
    </div>
    <div
      v-if="inlineRename.show"
      class="mm-overlay show"
      @click.self="$emit('close-rename')"
    >
      <div class="mm-ctx-rename-modal">
        <div class="mm-cat-modal-header">
          <span>{{ $t('mediaManager.ctxRename') }}</span>
          <button class="mm-btn-sm mm-close-btn" @click="$emit('close-rename')">
            <X :size="12" />
          </button>
        </div>
        <div class="mm-inline-rename-body">
          <input
            :ref="setRenameInput"
            :value="inlineRename.value"
            class="mm-cat-input mm-input-full"
            @input="$emit('update:rename-value', $event.target.value)"
            @keydown.enter="$emit('submit-rename')"
          />
        </div>
        <div class="mm-cat-modal-footer">
          <button class="mm-btn-sm" @click="$emit('close-rename')">
            {{ $t('common.cancel') }}
          </button>
          <button
            class="mm-btn-sm mm-btn-accent"
            :disabled="!inlineRename.value.trim()"
            @click="$emit('submit-rename')"
          >
            <Check :size="12" />
            {{ $t('mediaManager.ctxRename') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ArrowLeftRight, Check, Info, Pencil, Trash2, X } from 'lucide-vue-next'
import { FILE_TYPE } from '@/constants/mediaManager'

defineProps({
  ctxMenu: { type: Object, required: true },
  inlineRename: { type: Object, required: true },
  setRenameInput: { type: Function, required: true },
})
defineEmits(['ctx-rename', 'ctx-move', 'ctx-info', 'ctx-delete', 'submit-rename', 'close-rename', 'update:rename-value'])
</script>

<style scoped>
.mm-close-btn {
  padding: 3px 8px;
}
.mm-inline-rename-body {
  padding: 0.8rem 1rem;
}
.mm-input-full {
  width: 100%;
}
</style>
