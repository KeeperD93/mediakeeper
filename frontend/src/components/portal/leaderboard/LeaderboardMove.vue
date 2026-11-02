<template>
  <span class="gc-lb-move" :class="moveClass" :title="tooltip">
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

const props = defineProps({
  movement: { type: Number, default: 0 },
  size: { type: Number, default: 9 },
})

const { t } = useI18n()

const moveClass = computed(() => {
  if (!props.movement) return 'gc-lb-move--flat'
  return props.movement > 0 ? 'gc-lb-move--up' : 'gc-lb-move--down'
})

const tooltip = computed(() => {
  if (!props.movement) return t('portal.profile.rankStable')
  const key = props.movement > 0 ? 'portal.profile.rankUp' : 'portal.profile.rankDown'
  return t(key, { n: Math.abs(props.movement) })
})
</script>
