<template>
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
  <div v-if="hasMore" class="doub-load-more">
    <button class="doub-btn doub-btn-secondary" :disabled="loadingMore" @click="emit('load-more')">
      {{ $t('common.loadMore') }}
    </button>
  </div>
</template>

<script setup>
import { Check, Trash2 } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import { formatBytes, fmtDate } from '@/utils/duplicates'

defineProps({
  history: { type: Array, default: () => [] },
  hasMore: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
})
const emit = defineEmits(['load-more'])
</script>
