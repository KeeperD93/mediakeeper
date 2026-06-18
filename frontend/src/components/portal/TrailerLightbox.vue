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
      ref="panelRef"
      class="pt-tlb"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
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
        v-else-if="iframeSrc"
        :src="iframeSrc"
        frameborder="0"
        allow="autoplay; encrypted-media; fullscreen"
        sandbox="allow-scripts allow-same-origin allow-presentation"
        class="pt-tlb-media"
      />

      <button
        v-show="closeVisible"
        ref="closeBtnRef"
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { TRAILER_SOURCE } from '@/constants/trailers'
import { safeIframeSrc } from '@/utils/safeUrl'
import { X } from 'lucide-vue-next'

const props = defineProps({
  trailer: { type: Object, required: true },
})

// Only embed a validated absolute https URL (defence-in-depth: the backend
// already builds fixed YouTube/Vimeo schemes, but the iframe sink shouldn't
// trust its input). null -> the iframe simply isn't rendered.
const iframeSrc = computed(() => {
  const safe = safeIframeSrc(props.trailer.url)
  return safe ? `${safe}?autoplay=1&controls=1&rel=0&modestbranding=1&playsinline=1` : null
})

const emit = defineEmits(['close'])

// The close button is visible at mount (a 2.5s hide timer is armed in
// onMounted) and reappears for a few seconds every time the user moves
// the mouse — exactly like a fullscreen player.
const closeVisible = ref(true)
const panelRef = ref(null)
const closeBtnRef = ref(null)
let hideTimer = null

function showCloseTransient() {
  closeVisible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    closeVisible.value = false
  }, 2500)
}

function close() {
  emit('close')
}

onMounted(() => {
  // Lock body scroll while the lightbox is open.
  document.body.style.overflow = 'hidden'
  showCloseTransient()
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  if (hideTimer) clearTimeout(hideTimer)
})

useFocusTrap({
  active: ref(true),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
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
  border: 1px solid rgb(255, 255, 255, 0.4);
  background: rgb(0, 0, 0, 0.55);
  backdrop-filter: var(--portal-blur-xs);
  -webkit-backdrop-filter: var(--portal-blur-xs);
  color: var(--portal-text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    opacity var(--portal-dur-base) ease,
    transform var(--portal-dur-base) ease;
}
.pt-tlb-close:hover {
  background: rgb(0, 0, 0, 0.8);
  transform: translateX(-50%) scale(1.08);
}
</style>
