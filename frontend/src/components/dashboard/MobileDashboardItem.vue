<template>
  <div
    class="m-dash-item"
    :class="{
      'm-dash-item--editing': editing,
      'm-dash-item--placeholder': dragging,
      'm-dash-item--dimmed': dimmed,
    }"
    :style="dragging ? { height: dragHeight + 'px' } : null"
    :data-mobile-card-id="id"
  >
    <div
      class="m-dash-item__inner"
      :class="{ 'm-dash-item__inner--floating': dragging }"
      :style="dragging ? floatStyle : null"
    >
      <button
        v-if="editing"
        type="button"
        class="m-dash-item__handle"
        :aria-label="handleLabel"
        @touchstart.stop="$emit('handle-touchstart', $event)"
      >
        <GripHorizontal :size="22" :stroke-width="2.4" aria-hidden="true" />
      </button>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { GripHorizontal } from 'lucide-vue-next'

defineProps({
  id: { type: String, required: true },
  editing: { type: Boolean, default: false },
  dragging: { type: Boolean, default: false },
  dimmed: { type: Boolean, default: false },
  dragHeight: { type: Number, default: 0 },
  floatStyle: { type: Object, default: null },
  handleLabel: { type: String, default: '' },
})

defineEmits(['handle-touchstart'])
</script>

<style scoped>
.m-dash-item {
  min-height: 120px;
  /* ``pan-y`` keeps the browser's native vertical scroll usable during
     edit mode — users can swipe the dashboard without lifting a card
     until the 2 s long-press confirms they actually want to drag. */
  touch-action: pan-y;
  /* iOS/Android long-press would otherwise fire the text-selection
     callout before our 500 ms / 2 s timer elapses. Disable selection
     and the callout so the gesture wins cleanly. */
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  transition: opacity var(--duration-base) var(--ease-default);
}

.m-dash-item__inner {
  position: relative;
  transition:
    transform var(--duration-base) var(--ease-default),
    box-shadow var(--duration-base) var(--ease-default),
    opacity var(--duration-base) var(--ease-default);
}

/* Edit-mode drag handle — explicit grip the user can grab to lift a
   card instantly without waiting for the 2 s long-press to register.
   Top-centre placement so the gesture origin is unambiguous on every
   card width. The 44×44 hit box keeps Rules.md §2.6 happy while the
   visible glyph stays minimal (no chip, no halo). */
.m-dash-item__handle {
  position: absolute;
  top: 2px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--accent-300);
  cursor: grab;
  padding: 0;
  /* Lock the gesture even when the user lands on the visible glyph —
     pan-y on the card body is irrelevant once .stop fires on touch. */
  touch-action: none;
}

.m-dash-item__handle:active {
  cursor: grabbing;
  transform: translateX(-50%) scale(0.92);
}

.m-dash-item--editing .m-dash-item__inner {
  animation: m-dash-wiggle 1.4s ease-in-out infinite;
  transform-origin: 50% 50%;
}

/* The dragged card's slot becomes a placeholder — same height as the
   captured card so neighbours don't reflow vertically when the inner
   lifts into position: fixed, leaving a clearly visible dashed drop
   target where the card will land if released. */
.m-dash-item--placeholder {
  background: rgb(var(--accent-rgb), 0.08);
  border: 2px dashed rgb(var(--accent-rgb), 0.45);
  border-radius: var(--radius-card);
}
.m-dash-item--placeholder .m-dash-item__inner {
  visibility: hidden;
}

.m-dash-item--dimmed {
  opacity: 0.55;
}
.m-dash-item--dimmed .m-dash-item__inner {
  animation: none;
}

.m-dash-item__inner--floating {
  animation: none !important;
  transform: scale(1.06) rotate(1.2deg);
  /* Composite multi-layer shadow — kept as raw values per §3.7 because
     no single token captures the depth + accent halo combination. */
  box-shadow:
    0 24px 56px rgb(0, 0, 0, 0.55),
    0 0 0 2px var(--accent-400),
    0 0 32px rgb(var(--accent-rgb), 0.35);
  border-radius: var(--radius-card);
  /* The floating clone must not catch touches — they flow through to
     elementFromPoint so the swap logic can see the neighbour below. */
  pointer-events: none;
}

@keyframes m-dash-wiggle {
  0%,
  100% {
    transform: rotate(-0.4deg);
  }
  50% {
    transform: rotate(0.4deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .m-dash-item--editing .m-dash-item__inner {
    animation: none;
  }
}
</style>
