<template>
  <span class="wz-av" :class="[`wz-av--${size}`, tier && `wz-av--${tier}`]" aria-hidden="true">
    <img v-if="src && !failed" class="wz-av-img" :src="src" alt="" @error="failed = true" />
    <template v-else>{{ initial }}</template>
  </span>
</template>

<script setup>
import { ref, watch } from 'vue'

// The viewer's picture, or the first letter of their name when there is none
// (an Emby account without an image). Decorative: the name is written beside it.
const props = defineProps({
  src: { type: String, default: null },
  initial: { type: String, required: true },
  size: {
    type: String,
    default: 'sm',
    validator: value => ['sm', 'md', 'lg', 'hero'].includes(value),
  },
  // Rank tier (bronze → legendary): colours the ring.
  tier: { type: String, default: null },
})

const failed = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>
