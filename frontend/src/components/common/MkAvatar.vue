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

// Bigger silhouette (85%) on regular avatars (>= 32 px) so the icon
// actually fills the disc rather than floating tiny at the bottom. The
// chip range (< 32 px — leaderboard rows) stays at 80% to keep the
// glyph readable inside a tight tier ring.
const ICON_SCALE_CHIP = 0.8
const ICON_SCALE_FULL = 0.85
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
  align-items: flex-end;
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
  background: linear-gradient(135deg, var(--accent-500), var(--accent-600));
  /* Pure white silhouette on the accent gradient — semantic, no token. */
  color: #fff;
}

.mk-avatar-icon {
  /* Anchor the silhouette to the bottom of the circle so it reads as a
     framed head-and-shoulders portrait rather than a floating glyph. */
  margin-top: 8%;
}
</style>
