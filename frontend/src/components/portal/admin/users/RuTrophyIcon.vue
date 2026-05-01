<template>
  <span class="ru-trophy-icon" :class="{ 'ru-trophy-icon--muted': muted }">
    <component :is="resolved" :size="22" :stroke-width="1.8" />
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { ICON_MAP, Trophy, HelpCircle } from '@/utils/portal/iconMap'

const props = defineProps({
  icon: { type: String, default: '' },
  muted: { type: Boolean, default: false },
  secret: { type: Boolean, default: false },
})

const resolved = computed(() => {
  if (props.secret) return HelpCircle
  return ICON_MAP[props.icon] || Trophy
})
</script>
