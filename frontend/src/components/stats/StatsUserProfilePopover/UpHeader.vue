<template>
  <div class="up-header">
    <MkAvatar
      :src="profileAvatarUrl"
      :name="profileName"
      :size="42"
      :tier="profileTier || 'bronze'"
    />
    <div class="up-hinfo">
      <div class="up-name">{{ profileName }}</div>
      <div v-if="userProfile" class="up-sub">
        {{ userProfile.play_count?.toLocaleString(undefined) }} lectures —
        {{ ticksToDuration(userProfile.total_ticks) }}
      </div>
    </div>
    <MkButton
      variant="icon"
      size="sm"
      icon="x"
      :aria-label="$t('common.close')"
      @click="$emit('close')"
    />
  </div>
</template>

<script setup>
import MkAvatar from '@/components/common/MkAvatar.vue'
import MkButton from '@/components/common/MkButton.vue'

defineProps({
  profileName: { type: String, required: true },
  profileTier: { type: String, default: 'bronze' },
  profileAvatarUrl: { type: String, default: null },
  userProfile: { type: Object, default: null },
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
