<template>
  <Transition name="gc-toast">
    <div v-if="unlock" class="gc-unlock-toast" @click="$emit('dismiss')">
      <div class="gc-unlock-confetti">
        <span v-for="i in 20" :key="i" class="gc-confetti-bit" />
      </div>
      <div class="gc-unlock-icon">
        <component :is="iconMap[unlock.icon] || HelpCircle" :size="24" />
      </div>
      <div class="gc-unlock-info">
        <div class="gc-unlock-title">
          {{ $t('portal.profile.trophyUnlocked') || 'Achievement unlocked!' }}
        </div>
        <div class="gc-unlock-name">{{ $t(unlock.name_key) }}</div>
        <div class="gc-unlock-xp">+{{ unlock.xp_reward }} XP</div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { HelpCircle } from 'lucide-vue-next'

defineProps({
  unlock: { type: Object, default: null },
  iconMap: { type: Object, required: true },
})

defineEmits(['dismiss'])
</script>

<style>
@import url('@/assets/styles/portal/trophy-toast.css');
</style>
