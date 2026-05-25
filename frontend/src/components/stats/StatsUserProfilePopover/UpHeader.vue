<template>
  <div class="up-header">
    <div class="up-avatar" :style="{ background: avatarColors[0] }">
      {{ profileName[0]?.toUpperCase() }}
    </div>
    <div class="up-hinfo">
      <div class="up-name">{{ profileName }}</div>
      <div v-if="userProfile" class="up-sub">
        {{ userProfile.play_count?.toLocaleString(undefined) }} lectures —
        {{ ticksToDuration(userProfile.total_ticks) }}
      </div>
    </div>
    <button class="up-close" @click="$emit('close')">
      <X :size="14" :stroke-width="2.5" />
    </button>
  </div>
</template>

<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  profileName: { type: String, required: true },
  userProfile: { type: Object, default: null },
  avatarColors: { type: Array, required: true },
  ticksToDuration: { type: Function, required: true },
})
defineEmits(['close'])
</script>

<style scoped>
.up-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.up-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  flex-shrink: 0;
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
.up-sub {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 2px;
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

@media (max-width: 767px) {
  .up-header {
    position: sticky;
    top: -16px;
    z-index: 1;
    background: rgb(15, 20, 35, 0.97);
    margin: -16px -16px 16px;
    padding: 16px;
    border-bottom: 0.5px solid var(--border-default);
  }
}
</style>
