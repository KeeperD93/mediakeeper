<template>
  <Teleport to="body">
    <!-- From the avatar menu, where the browser has no install window of its own: the
         same steps as at the end of the first-login wizard. -->
    <div v-if="open" class="pis-overlay mk-modal-sheet" @click.self="close">
      <div
        ref="panelRef"
        class="pis-panel mk-modal-sheet-panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
      >
        <h2 :id="titleId" class="pis-title">{{ $t('portal.appInstall.title') }}</h2>
        <p class="pis-text">{{ $t('portal.appInstall.intro') }}</p>
        <p v-for="key in steps" :key="key" class="pis-text">{{ $t(key) }}</p>
        <button ref="closeRef" type="button" class="pis-close" @click="close">
          {{ $t('common.close') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, toRef, useId } from 'vue'
import { useAppInstall } from '@/composables/portal/useAppInstall'
import { useBodyScrollLock } from '@/composables/useBodyScrollLock'
import { useFocusTrap } from '@/composables/useFocusTrap'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const { steps } = useAppInstall()
const titleId = useId()
const panelRef = ref(null)
const closeRef = ref(null)

function close() {
  emit('close')
}

useBodyScrollLock(toRef(props, 'open'))
useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeRef,
  onEscape: close,
})
</script>

<style scoped>
/* The shared sheet (bottom of a phone, centered from 768px) in the portal's own look.
   main.css forces a radius on any class holding « -modal »: only !important sets ours. */
.pis-overlay.mk-modal-sheet {
  z-index: var(--portal-z-overlay);
  border-radius: 0 !important;
  background: var(--portal-overlay-modal);
  -webkit-backdrop-filter: var(--portal-blur-md);
  backdrop-filter: var(--portal-blur-md);
}
.pis-panel.mk-modal-sheet-panel {
  display: flex;
  flex-direction: column;
  gap: var(--portal-space-3);
  padding: var(--portal-space-3) var(--portal-space-6)
    calc(var(--portal-space-6) + env(safe-area-inset-bottom, 0px));
  border: var(--portal-border-width) solid var(--portal-border-default);
  border-radius: var(--portal-radius-2xl) var(--portal-radius-2xl) 0 0 !important;
  background: var(--portal-panel-bg);
  box-shadow: var(--portal-shadow-panel);
  color: var(--portal-text-primary-solid);
  animation-duration: var(--portal-dur-med);
  animation-timing-function: var(--portal-ease-out);
  outline: none;
}
.pis-panel.mk-modal-sheet-panel::before {
  background: var(--portal-border-intense);
  border-radius: var(--portal-radius-pill);
}
@media (min-width: 768px) {
  .pis-panel.mk-modal-sheet-panel {
    padding-top: var(--portal-space-6);
    border-radius: var(--portal-radius-2xl) !important;
  }
}

.pis-title {
  margin: 0;
  font-size: var(--portal-text-lg);
  font-weight: var(--portal-font-bold);
}
.pis-text {
  margin: 0;
  font-size: var(--portal-text-sm);
  line-height: var(--portal-lh-normal);
  color: var(--portal-text-secondary-solid);
}
.pis-close {
  align-self: flex-end;
  min-height: var(--portal-touch-target);
  margin-top: var(--portal-space-2);
  padding: var(--portal-space-2-5) var(--portal-space-4);
  border: var(--portal-border-width) solid var(--portal-border-strong);
  border-radius: var(--portal-radius-md);
  background: transparent;
  color: var(--portal-text-secondary-solid);
  font: inherit;
  font-size: var(--portal-text-base);
  cursor: pointer;
}
.pis-close:focus-visible {
  outline: var(--portal-focus-ring);
  outline-offset: var(--portal-focus-ring-offset);
}
@media (hover: hover) {
  .pis-close:hover {
    background: var(--portal-surface-3);
  }
}
</style>
