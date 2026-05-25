<template>
  <article
    class="arr-row arr-row--list"
    :class="[`arr-row--${barStatus}`, { 'arr-row--expanded': expanded }]"
  >
    <div class="arr-row-backdrop arr-row-backdrop--list" :style="backdropStyle" />
    <div class="arr-row-bar" />

    <div v-if="index !== null" class="arr-row-index">{{ String(index).padStart(2, '0') }}</div>

    <button
      class="arr-row-poster arr-row-poster--list"
      type="button"
      :aria-label="$t('portal.lists.actions.edit')"
      :aria-expanded="expanded"
      @click="$emit('toggle', lst.id)"
    >
      <div v-if="posterSlots.some(Boolean)" class="arr-row-poster-mosaic">
        <span
          v-for="(src, i) in posterSlots"
          :key="i"
          class="arr-row-poster-tile"
          :class="{ 'arr-row-poster-tile--empty': !src }"
        >
          <img v-if="src" :src="src" alt="" loading="lazy" />
        </span>
      </div>
      <FolderOpen v-else :size="38" :stroke-width="1.6" />
      <span class="arr-row-list-count">{{ lst.item_count }}</span>
    </button>

    <div class="arr-row-info">
      <div class="arr-row-meta-top">
        <span class="arr-row-type">
          {{ $t(`portal.lists.privacy.${lst.privacy}`) }}
        </span>
        <span class="arr-row-status">
          <span class="arr-row-status-dot" />
          {{ $t(`portal.lists.contentType.${lst.content_type || 'mixed'}`) }}
        </span>
      </div>
      <h3 class="arr-row-title">
        <span class="arr-row-title-text">{{ lst.name }}</span>
      </h3>
      <div class="arr-row-foot">
        <span v-if="!lst.is_owner">
          <span class="arr-who">{{ $t('portal.lists.ownedBy', { name: ownerLabel }) }}</span>
        </span>
        <span v-if="lst.copy_count > 0" class="arr-row-list-copies">↩ {{ lst.copy_count }}</span>
        <span v-if="lst.updated_at">
          <strong>{{ formatAgo(lst.updated_at) }}</strong>
        </span>
      </div>
    </div>

    <div class="arr-row-actions">
      <a
        class="arr-action arr-action--icon"
        :href="exportUrl(lst.id, 'csv')"
        target="_blank"
        rel="noopener"
        :title="$t('portal.lists.actions.exportCsv')"
        :aria-label="$t('portal.lists.actions.exportCsv')"
        @click.stop
      >
        <FileSpreadsheet :size="18" />
      </a>
      <a
        class="arr-action arr-action--icon"
        :href="exportUrl(lst.id, 'json')"
        target="_blank"
        rel="noopener"
        :title="$t('portal.lists.actions.exportJson')"
        :aria-label="$t('portal.lists.actions.exportJson')"
        @click.stop
      >
        <Download :size="18" :stroke-width="2.2" />
      </a>
      <button
        v-if="!lst.is_owner"
        class="arr-action arr-action--icon arr-action--available"
        type="button"
        :title="$t('portal.lists.actions.copy')"
        :aria-label="$t('portal.lists.actions.copy')"
        @click.prevent.stop="$emit('copy-list', lst)"
      >
        <Clipboard :size="18" :stroke-width="2.2" />
      </button>
      <button
        v-if="lst.is_owner"
        class="arr-action arr-action--icon"
        type="button"
        :title="$t('portal.lists.actions.edit')"
        :aria-label="$t('portal.lists.actions.edit')"
        @click.prevent.stop="$emit('edit', lst)"
      >
        <Pencil :size="18" :stroke-width="2.2" />
      </button>
      <button
        v-if="lst.is_owner"
        class="arr-action arr-action--icon arr-action--reject"
        type="button"
        :title="$t('portal.lists.actions.deleteList')"
        :aria-label="$t('portal.lists.actions.deleteList')"
        @click.prevent.stop="$emit('delete', lst)"
      >
        <Trash2 :size="18" />
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clipboard, Download, FileSpreadsheet, FolderOpen, Pencil, Trash2 } from 'lucide-vue-next'
import { formatAgo as formatAgoUtil } from '@/utils/formatAgo'

const props = defineProps({
  lst: { type: Object, required: true },
  index: { type: Number, default: null },
  expanded: { type: Boolean, default: false },
  exportUrl: { type: Function, required: true },
})
defineEmits(['toggle', 'edit', 'delete', 'copy-list'])

const { t } = useI18n()
const formatAgo = (input) => formatAgoUtil(input, t)

const PRIVACY_TO_BAR = {
  private: 'rejected',
  public_readonly: 'available',
  collaborative: 'pending',
}
const barStatus = computed(() => PRIVACY_TO_BAR[props.lst.privacy] || 'pending')

// Pad to exactly 4 slots for the 2×2 mosaic. Empty slots render
// a subtle placeholder so the tile grid stays square.
const posterSlots = computed(() => {
  const src = Array.isArray(props.lst.preview_posters) ? props.lst.preview_posters : []
  return [src[0] || null, src[1] || null, src[2] || null, src[3] || null]
})

const backdropStyle = computed(() => {
  const map = {
    private: 'rgba(156, 163, 175, 0.18)',
    public_readonly: 'rgba(34, 211, 238, 0.22)',
    collaborative: 'rgba(168, 85, 247, 0.22)',
  }
  const c = map[props.lst.privacy] || map.collaborative
  return { background: `radial-gradient(ellipse 50% 50% at 15% 50%, ${c}, transparent 70%)` }
})

const ownerLabel = computed(() => props.lst.contributors?.[0]?.username || `#${props.lst.owner_id}`)

</script>

<style scoped>
.arr-row-poster--list {
  border: none;
  cursor: pointer;
  background: var(--portal-gradient-glass-soft);
  color: var(--portal-text-body-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0;
}
.arr-row-list-count {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-black);
  color: var(--portal-text-primary);
  font-family: var(--portal-font-display);
  letter-spacing: var(--portal-tracking-tight);
  text-shadow: 0 0 10px rgb(0, 0, 0, 0.4);
}
.arr-row-list-copies {
  color: rgb(255, 255, 255, 0.6);
  font-weight: var(--portal-font-bold);
}

.arr-row-poster-mosaic {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px;
}
.arr-row-poster-tile {
  display: block;
  overflow: hidden;
  background: var(--portal-surface-2);
}
.arr-row-poster-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.arr-row-poster-tile--empty {
  background: rgb(255, 255, 255, 0.025);
}
.arr-row-poster--list:has(.arr-row-poster-mosaic) .arr-row-list-count {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 2px 7px;
  border-radius: var(--portal-radius-pill);
  background: rgb(0, 0, 0, 0.72);
  backdrop-filter: var(--portal-blur-xs);
  font-size: var(--portal-text-xs);
  text-shadow: none;
}
</style>
