<template>
  <Teleport to="body">
    <!-- Fades in, but leaves at once: a fade-out waits for the page behind to finish
         rendering before the window lets go of clicks. -->
    <div v-if="visible" class="dd-overlay" @click.self="dismissToday">
      <div
        ref="panelRef"
        class="dd-panel"
        :class="[
          compact ? 'dd-panel--compact' : 'dd-panel--full',
          { 'dd-panel--chained': chained },
        ]"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        tabindex="-1"
      >
        <!-- The window's name: the design shows no title, screen readers hear one. -->
        <span :id="titleId" class="sr-only">{{ $t('portal.dailyDigest.title') }}</span>
        <button
          type="button"
          class="dd-switch"
          role="switch"
          :aria-checked="compact ? 'true' : 'false'"
          @click="setCompact(!compact)"
        >
          <span>{{ $t('portal.dailyDigest.viewSwitch') }}</span>
          <span class="dd-switch-track"><span class="dd-switch-knob" /></span>
        </button>

        <!-- Loading, failed or nothing new: the message, then the way out. On a phone the
             window is the whole screen, and nothing else closes it there. -->
        <div v-if="!ready" class="dd-state-box">
          <p v-if="loading" class="dd-state">{{ $t('common.loading') }}</p>
          <p v-else-if="error" class="dd-state dd-state--error">
            {{ $t('portal.dailyDigest.errorLoad') }}
          </p>
          <p v-else class="dd-state">{{ $t('portal.dailyDigest.empty') }}</p>
          <button type="button" class="dd-cta" @click="dismissToday">
            {{ $t('common.close') }}
          </button>
        </div>
        <component
          :is="compact ? DigestCompact : DigestFull"
          v-else
          :digest="digest"
          @close="dismissToday"
          @leave="dismissToday"
          @read-news="readNews"
          @seen-news="noteNewsSeen"
          @open-release="openRelease"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// Loaded before the views, whose sheets refine these shared rules.
import '@/assets/styles/portal/daily-digest-shell.css'
import '@/assets/styles/portal/daily-digest-common.css'
import { computed, ref, watch, useId } from 'vue'
import { useBodyScrollLock } from '@/composables/useBodyScrollLock'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useDailyDigest } from '@/composables/portal/useDailyDigest'
import DigestCompact from '@/components/portal/daily-digest/DigestCompact.vue'
import DigestFull from '@/components/portal/daily-digest/DigestFull.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  auto: { type: Boolean, default: true },
  // Opened right after the first-login wizard, which wore the same window: the
  // backdrop is already there, only the window rises into place.
  chained: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const {
  digest,
  dismissed,
  compact,
  loading,
  error,
  load,
  dismiss,
  setCompact,
  readNews,
  noteNewsSeen,
  openRelease,
} = useDailyDigest()

const titleId = useId()
const visible = ref(false)
const panelRef = ref(null)
// Something to show: the view takes over, with its own way out at its foot.
const ready = computed(
  () => !loading.value && !error.value && !!digest.value && !digest.value.empty,
)

// By itself, the window opens only on a day it was not closed yet, with something to show.
async function openAuto() {
  const ok = await load()
  if (ok && !dismissed.value && digest.value && !digest.value.empty) visible.value = true
}

// From the avatar menu: open at once, then fill.
function openManual() {
  visible.value = true
  load({ force: true })
}

// Every way out (« Close » button, Escape, backdrop, a link followed) closes it for the day.
function dismissToday() {
  dismiss()
  visible.value = false
  emit('close')
}

// Lock the page behind: a gesture on the backdrop must not scroll it.
useBodyScrollLock(visible)

// Mounted already asked (after the wizard) or asked later (avatar menu): open at once.
watch(
  () => props.open,
  isOpen => {
    if (isOpen) openManual()
  },
  { immediate: true },
)

// The focus starts on the window itself: the only button to close it sits at its foot.
useFocusTrap({
  active: visible,
  containerRef: panelRef,
  onEscape: dismissToday,
})

if (props.auto) openAuto()
</script>
