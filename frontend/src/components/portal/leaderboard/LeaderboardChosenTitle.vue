<template>
  <em v-if="entry.selected_title" class="gc-lb-custom-title" :class="rarityClass">
    · {{ $t(entry.selected_title) }}
  </em>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  entry: { type: Object, required: true },
})

const RARITY_BY_TIER = {
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'epic',
  5: 'legendary',
  6: 'mythic',
}

const rarityClass = computed(() => {
  const tier = props.entry.title_tier
  return tier ? `gc-lb-custom-title--rarity-${RARITY_BY_TIER[tier] || 'common'}` : ''
})
</script>
