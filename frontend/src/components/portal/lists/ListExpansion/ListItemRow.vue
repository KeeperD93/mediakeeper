<template>
  <li class="ale-item">
    <router-link
      :to="{
        name: 'portal-media-detail',
        params: { type: item.media_type, id: item.tmdb_id },
      }"
      class="ale-item-link"
    >
      <span class="ale-item-poster">
        <img v-if="item.poster_url" :src="item.poster_url" :alt="item.title || ''" loading="lazy" />
        <span v-else class="ale-item-poster-fallback">
          {{ (item.title || '?').charAt(0) }}
        </span>
      </span>
      <span class="ale-item-main">
        <span class="ale-item-title-row">
          <span class="ale-item-title">{{ item.title || `#${item.tmdb_id}` }}</span>
          <button
            type="button"
            class="ale-item-copy"
            :title="copied ? $t('common.copied') : $t('common.copy')"
            :aria-label="$t('common.copy')"
            @click.prevent.stop="$emit('copy', item)"
          >
            <Copy v-if="!copied" :size="14" :stroke-width="2.2" />
            <Check v-else :size="14" :stroke-width="2.5" />
          </button>
        </span>
        <span class="ale-item-meta">
          <span class="ale-item-type">{{ item.media_type }}</span>
          <span v-if="item.year" class="ale-item-year">{{ item.year }}</span>
          <span class="ale-item-id">#{{ item.tmdb_id }}</span>
        </span>
      </span>
      <span class="ale-item-date">{{ formatDate(item.added_at) }}</span>
    </router-link>
    <button
      v-if="canEdit"
      class="ale-item-remove"
      type="button"
      :title="$t('common.delete')"
      :aria-label="$t('common.delete')"
      @click="$emit('remove', item.id)"
    >
      <X :size="14" :stroke-width="2.2" />
    </button>
  </li>
</template>

<script setup>
import { Check, Copy, X } from 'lucide-vue-next'

defineProps({
  item: { type: Object, required: true },
  copied: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: false },
  formatDate: { type: Function, required: true },
})
defineEmits(['copy', 'remove'])
</script>

<style scoped>
.ale-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-top: 1px solid var(--portal-border-faint);
  font-size: var(--portal-text-xs);
}
.ale-item:first-child {
  border-top: none;
}
.ale-item-link {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}
.ale-item-link:hover .ale-item-title {
  color: var(--accent-300);
}
.ale-item-poster {
  flex-shrink: 0;
  width: 40px;
  height: 60px;
  border-radius: var(--portal-radius-xs);
  overflow: hidden;
  background: var(--portal-surface-2);
  display: grid;
  place-items: center;
}
.ale-item-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ale-item-poster-fallback {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-extrabold);
  color: rgb(255, 255, 255, 0.3);
}
.ale-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ale-item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.ale-item-title {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-medium);
  color: var(--portal-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--portal-dur-fast);
  min-width: 0;
}
.ale-item-copy {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--portal-radius-pill);
  background: var(--portal-surface-3);
  border: 1px solid var(--portal-border-default);
  color: rgb(255, 255, 255, 0.65);
  cursor: pointer;
  opacity: 0;
  transform: translateX(-4px);
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    background 0.18s ease,
    color 0.18s ease,
    border-color 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .ale-item:hover .ale-item-copy {
    opacity: 1;
    transform: translateX(0);
  }
  .ale-item-copy:hover {
    background: rgb(var(--accent-rgb), 0.2);
    border-color: var(--accent-500);
    color: var(--portal-text-primary);
  }
}
@media (hover: none) {
  .ale-item-copy {
    opacity: 1;
    transform: none;
  }
}
.ale-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ale-item-type {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 7px;
  border-radius: var(--portal-radius-xs);
  background: rgb(var(--accent-rgb), 0.16);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.ale-item-year {
  font-size: var(--portal-text-2xs);
  color: var(--portal-text-secondary);
  font-weight: var(--portal-font-medium);
}
.ale-item-id {
  font-size: var(--portal-text-2xs);
  color: rgb(255, 255, 255, 0.35);
  font-weight: var(--portal-font-regular);
}
.ale-item-date {
  color: var(--portal-text-muted);
  font-size: var(--portal-text-2xs);
  margin-left: auto;
  flex-shrink: 0;
}
.ale-item-remove {
  width: 28px;
  height: 28px;
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--portal-radius-pill);
  border: 1px solid rgb(248, 113, 113, 0.3);
  background: transparent;
  color: var(--portal-color-error-soft);
  cursor: pointer;
  transition: all var(--portal-dur-fast);
  -webkit-tap-highlight-color: transparent;
}
.ale-item-remove:hover {
  background: rgb(248, 113, 113, 0.14);
  border-color: rgb(248, 113, 113, 0.6);
}
</style>
