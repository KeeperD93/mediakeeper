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

// Silhouette overscales the wrapper so the visible glyph (which lucide
// renders inside ~16% internal SVG padding) reads as a properly framed
// portrait. The ring is drawn by a CSS ``border`` on the wrapper, so
// the icon naturally fills the inner content area; bottom-anchored
// alignment clips the shoulder overflow at the circular border.
const ICON_SCALE_CHIP = 1.05
const ICON_SCALE_FULL = 1.2
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
  /* Anchor the silhouette to the bottom of the circle: the icon's
     shoulders curve overflows below the icon's vertical center, and
     centering ``align-items`` leaves the rounded bottom showing in
     the narrow visible band at the wrapper's bottom edge. Bottom-
     anchoring makes the circular clipping cut it cleanly. */
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  user-select: none;
  line-height: 1;
  /* Ring is a CSS border on the wrapper itself — no overlay SVG, no
     radial-gradient trickery. Border thickness + colour are driven by
     CSS variables so parent tier classes (gc-lb-av--gold, etc.) set
     them per rank without prop-drilling. Default = no ring. */
  border: var(--mk-avatar-ring-width, 0) solid
    var(--mk-avatar-ring-color, transparent);
  box-sizing: border-box;
}

.mk-avatar-circle {
  border-radius: 50%;
  /* ``clip-path`` enforces the circular cutout deterministically even
     when the browser is zoomed — ``overflow: hidden`` + ``border-
     radius`` alone leaks 1-2 px of the inner image past the rounded
     edge at non-integer zoom levels (Chrome/Edge especially). */
  clip-path: inset(0 round 50%);
}
.mk-avatar-square {
  border-radius: var(--radius-sm);
  clip-path: inset(0 round var(--radius-sm));
}

.mk-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.mk-avatar-icon {
  /* Always white regardless of the parent's ``color`` cascade — the
     border's tier colour is driven by the dedicated CSS variable so
     the icon doesn't pick it up. */
  color: #fff;
  /* Override the inline width/height bound to lucide's ``size`` prop
     so the silhouette tracks the RENDERED MkAvatar size (which CSS
     parent overrides like ``.gc-avatar-mk { width: 100% }`` can
     stretch beyond ``props.size``). Without these, daily digest's
     stretched 40 px disc still rendered a 28 px-derived icon and
     looked smaller than every other surface. 130% overscales so the
     visible silhouette (~67% of the SVG bbox due to lucide's
     internal padding) reads as a properly framed portrait. */
  width: 130% !important;
  height: 130% !important;
  flex-shrink: 1;
  /* Push the silhouette down so the head sits at the visual centre
     instead of riding the top edge. The icon SVG has the head in its
     top third — ``flex-end`` alone leaves a wide empty band above. */
  transform: translateY(15%);
}

.mk-avatar-fallback {
  /* Fully transparent: the parent tier-ring wrapper paints the
     coloured ring around us, the page background shows through the
     center. Only the white silhouette icon stays visible above. */
  background: transparent;
  color: #fff;
}
</style>

<!-- Non-scoped: reusable ring presets every consumer can stamp on
     ``<MkAvatar class="mk-avatar--ring-subtle">`` without re-declaring
     the custom properties on each call site. -->
<style>
.mk-avatar--ring-subtle {
  --mk-avatar-ring-width: 2px;
  --mk-avatar-ring-color: rgb(255, 255, 255, 0.18);
}
.mk-avatar--ring-thin {
  --mk-avatar-ring-width: 1.5px;
  --mk-avatar-ring-color: rgb(255, 255, 255, 0.2);
}
</style>
