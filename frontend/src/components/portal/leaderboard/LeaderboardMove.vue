<template>
  <span v-if="movement !== null" class="gc-lb-move" :class="moveClass" :title="tooltip">
    <ChevronUp v-if="movement > 0" :size="size" :stroke-width="3.5" />
    <ChevronDown v-else-if="movement < 0" :size="size" :stroke-width="3.5" />
    <span v-else>—</span>
    <span v-if="movement">{{ Math.abs(movement) }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import { LEADERBOARD_PERIOD } from '@/constants/leaderboard'

const props = defineProps({
  // Null when the period has no previous one to compare with: no badge at all.
  movement: { type: Number, default: 0 },
  period: { type: String, default: LEADERBOARD_PERIOD.MONTH },
  size: { type: Number, default: 9 },
})

const { t } = useI18n()

const moveClass = computed(() => {
  if (!props.movement) return 'gc-lb-move--flat'
  return props.movement > 0 ? 'gc-lb-move--up' : 'gc-lb-move--down'
})

const tooltip = computed(() => {
  const prefix = `portal.leaderboard.move.${props.period}`
  if (!props.movement) return t(`${prefix}.stable`)
  return t(`${prefix}.${props.movement > 0 ? 'up' : 'down'}`, { n: Math.abs(props.movement) })
})
</script>
