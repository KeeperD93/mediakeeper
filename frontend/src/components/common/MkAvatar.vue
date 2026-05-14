<template>
  <div
    class="mk-avatar"
    :class="['mk-avatar-' + shape, { 'mk-avatar-fallback': !showImage }]"
    :style="{
      width: size + 'px',
      height: size + 'px',
    }"
    :aria-label="name"
  >
    <img v-if="showImage" :src="src" :alt="name" class="mk-avatar-img" @error="onError" />
    <UserRound v-else :size="iconSize" :stroke-width="1.5" class="mk-avatar-icon" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { UserRound } from 'lucide-vue-next'

const props = defineProps({
  src: { type: String, default: null },
  name: { type: String, required: true },
  size: { type: Number, default: 32 },
  shape: {
    type: String,
    default: 'circle',
    validator: v => ['circle', 'square'].includes(v),
  },
})

const failed = ref(false)

watch(
  () => props.src,
  () => {
    failed.value = false
  },
)

const showImage = computed(() => !!props.src && !failed.value)

// Silhouette fills more of the visible disc now — 0.85 / 0.95 instead
// of 0.80 / 0.85. Combined with the dark interior fill, the icon reads
// as a properly framed portrait at every size from chip (24 px) to
// hero billboard (132 px).
const ICON_SCALE_CHIP = 0.85
const ICON_SCALE_FULL = 0.95
const iconSize = computed(() =>
  Math.round(props.size * (props.size < 32 ? ICON_SCALE_CHIP : ICON_SCALE_FULL)),
)

function onError() {
  failed.value = true
}
</script>

<style scoped>
.mk-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  user-select: none;
  line-height: 1;
}

.mk-avatar-circle {
  border-radius: 50%;
}
.mk-avatar-square {
  border-radius: var(--radius-sm);
}

.mk-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.mk-avatar-fallback {
  /* Match the dark page background so the tier ring drawn by the
     parent wrapper (gc-lb-av, lb-hero-avatar, etc.) is the only
     coloured framing around the silhouette — previously the accent
     gradient painted an unwanted purple disc inside every ring. */
  background: var(--bg-primary);
  color: #fff;
}
</style>
