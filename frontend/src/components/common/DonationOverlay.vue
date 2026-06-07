<template>
  <Teleport to="body">
    <transition name="dn-fade">
      <div
        v-if="open"
        class="dn-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="close"
      >
        <div ref="panelRef" class="dn-panel mk-modal-sheet-panel" tabindex="-1">
          <header class="dn-header">
            <h2 :id="titleId" class="dn-title">
              <Heart class="dn-title-icon" :size="18" fill="currentColor" :stroke-width="0" />
              {{ $t('donation.panelTitle') }}
            </h2>
            <button
              ref="closeBtnRef"
              class="dn-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="close"
            >
              <X :size="16" />
            </button>
          </header>

          <div class="dn-body">
            <!-- MediaKeeper project support — admin only. -->
            <section v-if="isAdmin" class="dn-section">
              <h3 class="dn-section-title">{{ $t('donation.mkTitle') }}</h3>
              <p class="dn-intro">{{ $t('donation.mkIntro') }}</p>
              <a
                class="dn-cta dn-cta--primary"
                :href="links.kofi"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Coffee :size="16" />
                <span>{{ $t('donation.kofi') }}</span>
              </a>
              <a
                v-if="links.sponsor"
                class="dn-cta"
                :href="links.sponsor"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Github :size="16" />
                <span>{{ $t('donation.sponsor') }}</span>
              </a>
              <a class="dn-cta" :href="links.repo" target="_blank" rel="noopener noreferrer">
                <Star :size="16" />
                <span>{{ $t('donation.star') }}</span>
              </a>
            </section>

            <!-- Operator's own donation appeal — visible to everyone when set. -->
            <section v-if="showInstance" class="dn-section dn-section--instance">
              <h3 class="dn-section-title">{{ $t('donation.instanceTitle') }}</h3>
              <p class="dn-intro">{{ donation.message || $t('donation.instanceIntro') }}</p>
              <a
                class="dn-cta dn-cta--primary"
                :href="instanceHref"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Heart :size="16" />
                <span>{{ $t('donation.instanceCta') }}</span>
              </a>
            </section>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, toRef, useId } from 'vue'
import { Coffee, Github, Heart, Star, X } from 'lucide-vue-next'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { safeHref } from '@/utils/safeUrl'
import { MEDIAKEEPER_SUPPORT } from '@/constants/donation'

const props = defineProps({
  open: { type: Boolean, default: false },
  isAdmin: { type: Boolean, default: false },
  donation: { type: Object, default: null },
})
const emit = defineEmits(['close'])

const links = MEDIAKEEPER_SUPPORT
const titleId = useId()
const panelRef = ref(null)
const closeBtnRef = ref(null)

// Defence in depth: the backend already rejects non-http(s) links, but the
// panel re-checks before rendering the operator's user-supplied URL.
const instanceHref = computed(() => safeHref(props.donation?.url || ''))
const showInstance = computed(() => !!props.donation?.enabled && !!instanceHref.value)

function close() {
  emit('close')
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>

<style scoped>
.dn-overlay {
  z-index: 9998;
}
.dn-panel {
  display: flex;
  flex-direction: column;
  background: var(--surface-1);
  border: 1px solid var(--border-default);
  outline: none;
}
@media (min-width: 768px) {
  .dn-panel {
    max-width: 460px;
  }
}

.dn-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 8px;
}
.dn-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.dn-title-icon {
  color: var(--accent-500);
}
.dn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border: none;
  border-radius: var(--radius-btn);
  background: var(--surface-2);
  color: var(--text-muted);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .dn-close:hover {
    background: var(--surface-3);
    color: var(--text-primary);
  }
}
.dn-close:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgb(var(--accent-rgb), 0.4);
}

.dn-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 8px 20px 22px;
}
.dn-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.dn-section--instance {
  padding-top: 18px;
  border-top: 1px solid var(--border-default);
}
.dn-section-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.dn-intro {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.55;
  color: var(--text-secondary);
}
.dn-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 16px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border-default);
  background: var(--surface-2);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}
.dn-cta svg {
  flex-shrink: 0;
  color: var(--accent-300);
}
@media (hover: hover) {
  .dn-cta:hover {
    background: var(--surface-3);
    border-color: var(--border-hover);
  }
}
.dn-cta:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgb(var(--accent-rgb), 0.4);
}
.dn-cta--primary {
  border-color: transparent;
  background: var(--accent-500);
  color: var(--color-on-accent);
  box-shadow: 0 6px 20px rgb(var(--accent-rgb), 0.35);
}
.dn-cta--primary svg {
  color: var(--color-on-accent);
}
@media (hover: hover) {
  .dn-cta--primary:hover {
    background: var(--accent-600);
    border-color: transparent;
  }
}

.dn-fade-enter-active {
  transition: opacity var(--duration-base) var(--ease-out);
}
.dn-fade-leave-active {
  transition: opacity var(--duration-fast) var(--ease-out);
}
.dn-fade-enter-from,
.dn-fade-leave-to {
  opacity: 0;
}
</style>
