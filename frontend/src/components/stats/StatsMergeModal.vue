<template>
  <div v-if="mergeModal.open" class="up-overlay" @click="mergeModal.open = false" />
  <Transition name="pop-profile">
    <div v-if="mergeModal.open" class="up-pop merge-modal">
      <div class="up-header">
        <div class="up-hinfo merge-hinfo">
          <div class="up-name">{{ $t('stats.mergeTitle') }}</div>
        </div>
        <MkButton
          variant="icon"
          size="sm"
          icon="x"
          :aria-label="$t('common.close')"
          @click="mergeModal.open = false"
        />
      </div>
      <div class="merge-source-box">
        <span class="merge-label merge-label-source">{{ $t('stats.mergeSource') }}</span>
        <div class="merge-user-pill">
          <MkAvatar
            :src="mergeModal.source?.avatar_url"
            :name="mergeModal.source?.name || '?'"
            :size="24"
            :tier="mergeModal.source?.tier || 'bronze'"
          />
          <span>{{ mergeModal.source?.name }}</span>
          <span class="merge-item-plays">
            {{ mergeModal.source?.play_count || 0 }} {{ $t('stats.plays').toLowerCase() }}
          </span>
        </div>
        <p class="merge-source-hint">{{ $t('stats.mergeSourceHint') }}</p>
      </div>
      <div class="merge-arrow-row">
        <ArrowDown :size="16" />
      </div>
      <span class="merge-label merge-label-target">{{ $t('stats.mergeTarget') }}</span>
      <input
        v-model="mergeModal.search"
        class="ctrl-search merge-search"
        :placeholder="$t('common.search') + '...'"
      />
      <div class="merge-list">
        <div
          v-for="u in mergeTargets"
          :key="u.user_id"
          class="merge-item"
          :class="{ active: mergeModal.targetId === u.user_id }"
          @click="mergeModal.targetId = u.user_id"
        >
          <MkAvatar
            :src="u.avatar_url"
            :name="u.name || '?'"
            :size="28"
            :tier="u.tier || 'bronze'"
          />
          <span class="merge-item-name">{{ u.name }}</span>
          <span class="merge-item-plays">
            {{ u.play_count }} {{ $t('stats.plays').toLowerCase() }}
          </span>
        </div>
        <div v-if="!mergeTargets.length" class="up-empty">{{ $t('stats.noUsers') }}</div>
      </div>
      <div class="merge-actions">
        <MkButton
          variant="primary"
          icon="shuffle"
          :disabled="!mergeModal.targetId"
          @click="handleMerge"
        >
          {{ $t('stats.mergeConfirm') }}
        </MkButton>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useStatsUI } from '@/composables/useStatsUI'
import { ArrowDown } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import MkButton from '@/components/common/MkButton.vue'
const { mergeModal, mergeTargets, handleMerge } = useStatsUI()
</script>

<style scoped>
.up-overlay {
  position: fixed;
  inset: 0;
  z-index: 900;
}
.up-pop {
  position: fixed;
  z-index: 901;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 420px;
  max-width: calc(100vw - 24px);
  background: rgb(15, 20, 35, 0.97);
  backdrop-filter: blur(24px);
  border: 0.5px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: 0 20px 60px rgb(0, 0, 0, 0.4);
}
.pop-profile-enter-active,
.pop-profile-leave-active {
  transition: all var(--duration-base) ease;
}
.pop-profile-enter-from,
.pop-profile-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) translateY(6px);
}
.up-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.up-hinfo {
  flex: 1;
  min-width: 0;
}
.up-name {
  font-size: var(--text-md);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.up-close {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-btn);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.up-close:hover {
  background: rgb(239, 68, 68, 0.1);
  color: var(--color-error);
  border-color: rgb(239, 68, 68, 0.2);
}
.up-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 12px 0;
}

.merge-search {
  margin: 6px 0 10px;
  width: 100%;
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  border-radius: var(--radius-btn);
  padding: 6px 12px;
  font-size: var(--text-xs);
  color: var(--text-primary);
  outline: none;
}
.merge-list {
  max-height: 280px;
  overflow-y: auto;
  margin: 0 -4px;
  padding: 0 4px;
}
.merge-list::-webkit-scrollbar {
  width: 4px;
}
.merge-list::-webkit-scrollbar-thumb {
  background: rgb(255, 255, 255, 0.1);
  border-radius: 2px;
}
.merge-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: all 0.12s;
  border: 1px solid transparent;
}
.merge-item:hover {
  background: var(--surface-2);
}
.merge-item.active {
  border-color: var(--accent-500);
  background: rgb(var(--accent-rgb), 0.08);
}
.merge-item-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  color: var(--text-primary);
}
.merge-item-plays {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.merge-source-box {
  background: rgb(239, 68, 68, 0.06);
  border: 1px solid rgb(239, 68, 68, 0.15);
  border-radius: var(--radius-btn);
  padding: 10px 12px;
  margin-bottom: 4px;
}
.merge-source-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: 6px 0 0;
  font-style: italic;
}
.merge-user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  color: var(--text-primary);
}
.merge-label {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: var(--font-medium);
  margin-bottom: 4px;
  display: block;
}
.merge-label-source {
  color: var(--color-error);
}
.merge-label-target {
  color: var(--color-success);
}
.merge-arrow-row {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  color: var(--text-muted);
}
.merge-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.params-save-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: var(--radius-btn);
  background: var(--accent-600);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  font-family: inherit;
  border: none;
  cursor: pointer;
  transition: all var(--duration-base);
}
.params-save-btn:hover:not(:disabled) {
  background: var(--accent-500);
}
.params-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.merge-hinfo {
  flex: 1;
}
</style>
