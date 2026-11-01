<template>
  <button
    ref="pill"
    type="button"
    class="sec-pill is-cleared"
    :aria-describedby="spot ? hintId : undefined"
    @mouseenter="show"
    @mouseleave="hide"
    @focus="show"
    @blur="hide"
    @click="show"
    @keydown.esc="hide"
  >
    {{ t('settings.security.cleared') }}
    <!-- On the body: the table's scroll area would cut it off. -->
    <Teleport to="body">
      <span
        v-if="spot"
        :id="hintId"
        role="tooltip"
        class="sec-cleared-hint"
        :class="{ 'is-above': opensUp }"
        :style="spot"
      >
        {{ t('settings.security.clearedHint') }}
      </span>
    </Teleport>
  </button>
</template>

<script setup>
import { onBeforeUnmount, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { rootZoom } from '@/utils/zoom'

const { t } = useI18n()
const hintId = useId()
const pill = ref(null)
const spot = ref(null) // where the explanation sits on screen; null while closed
const opensUp = ref(false)

function closeOnPressElsewhere(event) {
  if (!pill.value.contains(event.target)) hide()
}

function show() {
  const zoom = rootZoom() // admin zoom: divide the final position (utils/zoom)
  const rect = pill.value.getBoundingClientRect()
  // Towards the roomier half of the screen, so it never leaves it.
  opensUp.value = rect.top > window.innerHeight / 2
  spot.value = {
    left: `${rect.right / zoom}px`,
    top: `${(opensUp.value ? rect.top : rect.bottom) / zoom}px`,
  }
  // A finger never "leaves" the pill, and a fixed box cannot follow the page.
  document.addEventListener('pointerdown', closeOnPressElsewhere)
  window.addEventListener('scroll', hide, true)
  window.addEventListener('resize', hide)
}

function hide() {
  spot.value = null
  document.removeEventListener('pointerdown', closeOnPressElsewhere)
  window.removeEventListener('scroll', hide, true)
  window.removeEventListener('resize', hide)
}

onBeforeUnmount(hide)
</script>

<style scoped>
.is-cleared {
  position: relative;
  border: none;
  background: var(--surface-2);
  color: var(--text-muted);
  text-decoration: underline dotted;
  cursor: help;
}
/* A 44 px touch band on phones; the pill keeps its look. */
.is-cleared::after {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: var(--touch-target);
  transform: translateY(-50%);
}
@media (min-width: 768px) {
  .is-cleared::after {
    content: none;
  }
}
/* Grows leftwards from the pill's right edge: on a phone the pill sits at the
   screen's right side. max-content, or the little room left of "left" squeezes it. */
.sec-cleared-hint {
  position: fixed;
  z-index: var(--z-dropdown);
  width: max-content;
  max-width: min(40ch, 100vw - var(--space-8));
  padding: var(--space-2) var(--space-3);
  border: var(--border-width) solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--overlay-bg);
  color: var(--text-primary);
  font-size: var(--text-xs);
  box-shadow: var(--shadow-popover);
  transform: translate(-100%, var(--space-1));
}
.sec-cleared-hint.is-above {
  transform: translate(-100%, calc(-100% - var(--space-1)));
}
</style>
