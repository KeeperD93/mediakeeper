<template>
  <MkEmptyState
    v-if="!items.length"
    :title="$t('duplicates.noIgnored')"
    :sub="$t('duplicates.ignoredHint')"
  />
  <div v-else>
    <div class="dig-header">
      <p class="dig-count">
        {{ $t('duplicates.ignoredCount', { count: items.length }) }}
      </p>
      <button
        type="button"
        class="dig-restore-all"
        :aria-label="$t('common.restoreAll')"
        @click="onRestoreAll"
      >
        {{ $t('common.restoreAll') }}
      </button>
    </div>
    <div class="dig-list">
      <div v-for="g in grouped" :key="groupKey(g)" class="dig-row glass-row">
        <div class="dig-row-name" :title="g.name">{{ g.name }}</div>
        <div v-if="g.type === 'series'" class="dig-tags">
          <span v-for="ep in g.eps" :key="ep.key" class="dig-tag">
            S{{ pad(ep.season) }}E{{ pad(ep.episode) }}
            <button
              type="button"
              class="dig-tag-x"
              :aria-label="$t('common.restore')"
              :title="$t('common.restore')"
              @click="$emit('restore', [ep.key])"
            >
              ✕
            </button>
          </span>
        </div>
        <button
          type="button"
          class="dig-restore-row"
          :aria-label="$t('common.restore')"
          @click="$emit('restore', g.keys)"
        >
          {{ $t('common.restore') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import { groupIgnoredDuplicates } from './groupIgnoredDuplicates'

const props = defineProps({
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['restore'])
const { t } = useI18n()
const mkConfirm = useConfirm()

const grouped = computed(() => groupIgnoredDuplicates(props.items))

function pad(n) {
  return String(n).padStart(2, '0')
}

function groupKey(g) {
  return g.type === 'series' ? `s:${g.name}` : `m:${g.key}`
}

async function onRestoreAll() {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.restore'),
    message: t('duplicates.restoreAllConfirm', { n: props.items.length }),
    variant: 'warn',
  })
  if (!ok) return
  emit(
    'restore',
    props.items.map(i => i.key),
  )
}
</script>

<style scoped>
.dig-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}
.dig-count {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.dig-restore-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 14px;
  border-radius: var(--radius-btn);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-base);
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  font-family: inherit;
}
@media (hover: hover) {
  .dig-restore-all:hover {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}

.dig-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.glass-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: var(--surface-1);
  backdrop-filter: var(--blur-sm);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-btn);
  transition: border-color var(--duration-fast);
}
.glass-row:hover {
  border-color: rgb(99, 102, 241, 0.2);
}
.dig-row-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  width: 200px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dig-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex: 1;
  min-width: 0;
}
.dig-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-3xs);
  font-family: 'SF Mono', monospace;
  padding: 2px 7px;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--text-secondary);
  border: 0.5px solid rgb(255, 255, 255, 0.07);
}
.dig-tag-x {
  background: none;
  border: none;
  color: rgb(156, 163, 175, 0.5);
  cursor: pointer;
  font-size: 0.55rem;
  padding: 0;
  transition: color var(--duration-fast);
  line-height: var(--lh-tight);
}
.dig-tag-x:hover {
  color: var(--color-error);
}
.dig-restore-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: var(--radius-btn);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-2xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-base);
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  font-family: inherit;
  flex-shrink: 0;
  margin-left: auto;
}
@media (hover: hover) {
  .dig-restore-row:hover {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}

@media (max-width: 767px) {
  .glass-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 12px;
  }
  .dig-row-name {
    width: auto;
    flex: none;
  }
  .dig-tags {
    width: 100%;
    gap: 5px;
    flex: none;
  }
  .dig-tag {
    font-size: var(--text-2xs);
    padding: 3px 8px;
    min-height: 26px;
  }
  .dig-tag-x {
    font-size: var(--text-2xs);
    min-width: 18px;
    min-height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .dig-restore-row {
    align-self: flex-end;
    min-height: 32px;
    padding: 6px 12px;
    font-size: var(--text-2xs);
  }
  .dig-restore-all {
    min-height: 44px;
  }
}
</style>
