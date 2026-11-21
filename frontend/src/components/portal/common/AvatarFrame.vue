<template>
  <div
    class="pt-avf"
    :class="{ 'pt-avf--own': !$slots.default, 'pt-avf--fx': fx, 'pt-avf--reserve': reserve && fx }"
    :style="{ '--pt-avf-default': size }"
  >
    <!-- The element types and their order matter: the effects' styles count them
         (nth-of-type), as they did around the rank card's avatar. -->
    <div v-if="fx && fx !== 'ranking'" class="pt-avf-layer" :class="fxClass" aria-hidden="true">
      <template v-if="fx === 'dedication'">
        <div class="gc-fx-comet-core" />
        <div class="gc-fx-comet-trail" />
        <div class="gc-fx-comet-head" />
      </template>
      <template v-else-if="fx === 'special'">
        <div class="gc-fx-holy-rays" />
        <div class="gc-fx-holy-glow" />
        <div class="gc-fx-holy-ring" />
        <div v-for="i in 4" :key="'rune' + i" class="gc-fx-rune" />
      </template>
      <template v-else-if="fx === 'community'">
        <div class="gc-fx-nebula" />
        <span v-for="i in 8" :key="'star' + i" class="gc-fx-star" />
      </template>
      <template v-else-if="fx === 'meta'">
        <div class="gc-fx-mandala gc-fx-mandala--dots" />
        <div class="gc-fx-mandala gc-fx-mandala--outer" />
        <div class="gc-fx-mandala gc-fx-mandala--mid" />
        <div class="gc-fx-mandala gc-fx-mandala--inner" />
      </template>
    </div>

    <slot>
      <MkAvatar class="pt-avf-avatar" :src="src" :name="name" :size="size" :tier="tier" />
    </slot>

    <!-- The ranking stars and their halos pass in front of the avatar. -->
    <div
      v-if="fx === 'ranking'"
      class="pt-avf-layer pt-avf-layer--top"
      :class="fxClass"
      aria-hidden="true"
    >
      <div v-for="i in 5" :key="'halo' + i" class="gc-fx-rhalo" :class="`gc-fx-rhalo--${i}`" />
      <div v-for="i in 5" :key="'star' + i" class="gc-fx-rstar" :class="`gc-fx-rstar--${i}`" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MkAvatar from '@/components/common/MkAvatar.vue'
import { AVATAR_EFFECTS } from '@/constants/portal'
import '@/assets/styles/portal/trophy-master-avatar-fx.css'
import '@/assets/styles/portal/avatar-frame.css'

const props = defineProps({
  src: { type: String, default: null },
  name: { type: String, default: '' },
  // In pixels: the avatar's, and the scale of its frame. The page can change it per
  // layout with the --pt-avf-size property.
  size: { type: Number, default: 40 },
  tier: { type: String, default: null },
  // The frame chosen by the player (`avatar_effect`); an unknown one draws nothing.
  effect: { type: String, default: null },
  // Lay the whole frame out instead of letting it spill over the neighbours.
  reserve: { type: Boolean, default: false },
})

const fx = computed(() => (AVATAR_EFFECTS.includes(props.effect) ? props.effect : null))
const fxClass = computed(() => `gc-avatar-fx--${fx.value}`)
</script>
