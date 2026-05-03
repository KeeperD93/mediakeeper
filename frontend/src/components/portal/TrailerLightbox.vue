<template>
  <!--
    Fullscreen trailer lightbox.

    - Closes on Escape, on click of the floating close button (which only
      appears when the user moves their mouse) or on backdrop click.
    - Renders either a real <video> tag (Emby local trailer streamed via
      the backend proxy) or a sandboxed iframe (YouTube/Vimeo).
    - Uses the trailer descriptor produced by the backend cascade so the
      correct language and source are honoured automatically.
  -->
  <Teleport to="body">
    <div
      class="pt-tlb"
      role="dialog"
      aria-modal="true"
      @click.self="close"
      @mousemove="showCloseTransient"
    >
      <video
        v-if="trailer.source === TRAILER_SOURCE.EMBY"
        :src="trailer.url"
        autoplay
        controls
        playsinline
        class="pt-tlb-media"
      />
      <iframe
        v-else
        :src="`${trailer.url}?autoplay=1&controls=1&rel=0&modestbranding=1&playsinline=1`"
        frameborder="0"
        allow="autoplay; encrypted-media; fullscreen"
        sandbox="allow-scripts allow-same-origin allow-presentation"
        class="pt-tlb-media"
      />

      <button
        v-show="closeVisible"
        class="pt-tlb-close"
        :aria-label="$t('common.close')"
        @click="close"
      >
        <X :size="22" :stroke-width="2.5" />
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { TRAILER_SOURCE } from '@/constants/trailers'
import { X } from 'lucide-vue-next'

defineProps({
  trailer: { type: Object, required: true },
})

const emit = defineEmits(['close'])

// The close button is hidden by default and reappears for a few seconds
// every time the user moves the mouse — exactly like a fullscreen player.
const closeVisible = ref(false)
let hideTimer = null

function showCloseTransient() {
  closeVisible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { closeVisible.value = false }, 2500)
}

function close() {
  emit('close')
}

function onKey(e) {
  if (e.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('keydown', onKey)
  // Lock body scroll while the lightbox is open.
  document.body.style.overflow = 'hidden'
  showCloseTransient()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<style scoped>
.pt-tlb {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}
.pt-tlb-media {
  width: 100vw;
  height: 100vh;
  max-width: 100vw;
  max-height: 100vh;
  border: none;
  background: #000;
  /* contain so we never crop the trailer in fullscreen — letterboxing
     is acceptable here, the goal is to see the whole image. */
  object-fit: contain;
}
.pt-tlb-close {
  position: fixed;
  top: 1.25rem;
  left: 50%;
  transform: translateX(-50%);
  width: 48px;
  height: 48px;
  border-radius: var(--portal-radius-circle);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: var(--portal-blur-xs);
  -webkit-backdrop-filter: var(--portal-blur-xs);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity var(--portal-dur-base) ease, transform var(--portal-dur-base) ease;
}
.pt-tlb-close:hover {
  background: rgba(0, 0, 0, 0.8);
  transform: translateX(-50%) scale(1.08);
}
</style>
