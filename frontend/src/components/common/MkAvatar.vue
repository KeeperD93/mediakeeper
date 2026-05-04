<template>
  <div
    class="mk-avatar"
    :class="['mk-avatar-' + shape, { 'mk-avatar-fallback': !showImage }]"
    :style="{
      width: size + 'px',
      height: size + 'px',
      fontSize: fontSize + 'px',
    }"
    :aria-label="name"
  >
    <img v-if="showImage" :src="src" :alt="name" class="mk-avatar-img" @error="onError" />
    <span v-else class="mk-avatar-letter">{{ letter }}</span>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

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

const letter = computed(() => {
  const n = (props.name || '').trim()
  return n ? n.charAt(0).toUpperCase() : '?'
})

const fontSize = computed(() => Math.round(props.size * 0.4))

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
  background: linear-gradient(135deg, var(--accent-500), var(--accent-600));
  color: #fff;
  font-weight: var(--font-bold);
  text-transform: uppercase;
}

.mk-avatar-letter {
  display: inline-block;
  line-height: 1;
}
</style>
