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
          <button
            ref="closeBtnRef"
            class="dn-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="close"
          >
            <X :size="16" />
          </button>

          <header class="dn-hero">
            <span class="dn-hero-glyph">
              <Heart
                class="dn-hero-heart"
                :size="44"
                fill="currentColor"
                stroke="currentColor"
                :stroke-width="1.5"
              />
            </span>
            <h2 :id="titleId" class="dn-hero-title">{{ $t('donation.panelTitle') }}</h2>
          </header>

          <div class="dn-body">
            <!-- MediaKeeper project support — admin only. -->
            <section v-if="isAdmin" class="dn-section">
              <h3 class="dn-section-title">{{ $t('donation.mkTitle') }}</h3>
              <p class="dn-intro">{{ $t('donation.mkIntro') }}</p>
              <h3 class="dn-how">{{ $t('donation.mkHow') }}</h3>

              <a
                class="dn-cta dn-cta--primary"
                :href="links.kofi"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span class="dn-cta-icon"><Coffee :size="20" /></span>
                <span class="dn-cta-text">
                  <span class="dn-cta-label">{{ $t('donation.kofi') }}</span>
                  <span class="dn-cta-sub">{{ $t('donation.kofiSub') }}</span>
                </span>
                <ArrowUpRight class="dn-cta-arrow" :size="18" />
              </a>

              <a
                v-if="links.sponsor"
                class="dn-cta dn-cta--sponsor"
                :href="links.sponsor"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span class="dn-cta-icon"><Github :size="20" /></span>
                <span class="dn-cta-text">
                  <span class="dn-cta-label">{{ $t('donation.sponsor') }}</span>
                  <span class="dn-cta-sub">{{ $t('donation.sponsorSub') }}</span>
                </span>
                <ArrowUpRight class="dn-cta-arrow" :size="18" />
              </a>

              <a
                class="dn-cta dn-cta--star"
                :href="links.repo"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span class="dn-cta-icon"><Star :size="20" /></span>
                <span class="dn-cta-text">
                  <span class="dn-cta-label">{{ $t('donation.star') }}</span>
                  <span class="dn-cta-sub">{{ $t('donation.starSub') }}</span>
                </span>
                <ArrowUpRight class="dn-cta-arrow" :size="18" />
              </a>

              <p class="dn-thanks">{{ $t('donation.mkThanks') }}</p>
            </section>

            <!-- Operator's own donation appeal — everyone when configured. -->
            <section v-if="showInstance" class="dn-section dn-section--instance">
              <h3 class="dn-section-title">{{ $t('donation.instanceTitle') }}</h3>
              <!-- Server sanitises on write; DOMPurify here is defence in depth. -->
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div v-if="messageHtml" class="dn-quote" v-html="messageHtml" />
              <p v-else class="dn-quote">{{ $t('donation.instanceIntro') }}</p>
              <a
                class="dn-cta dn-cta--primary"
                :href="instanceHref"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span class="dn-cta-icon"><Heart :size="20" /></span>
                <span class="dn-cta-text">
                  <span class="dn-cta-label">
                    {{ donation.button_label || $t('donation.instanceCta') }}
                  </span>
                </span>
                <ArrowUpRight class="dn-cta-arrow" :size="18" />
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
import DOMPurify from 'dompurify'
import { ArrowUpRight, Coffee, Github, Heart, Star, X } from 'lucide-vue-next'
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

// The operator message is sanitised HTML (bleach server-side). Re-purify
// before v-html as defence in depth; empty/blank content falls back to the
// default intro line.
const messageHtml = computed(() => {
  const raw = props.donation?.message || ''
  if (!raw.replace(/<[^>]*>/g, '').trim()) return ''
  return DOMPurify.sanitize(raw)
})

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
  position: relative;
  display: flex;
  flex-direction: column;
  /* Opaque premium surface — a soft red glow at the top fades into the solid
     panel colour (no see-through glass). */
  background:
    radial-gradient(125% 70% at 50% 0%, rgb(var(--color-error-strong-rgb), 0.16), transparent 58%),
    var(--bg-secondary);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-xl);
  outline: none;
}
/* Fixed, roomy panel on desktop (mobile keeps the full-width bottom sheet). */
@media (min-width: 768px) {
  .dn-panel {
    width: 520px;
    max-width: 92vw;
    min-height: 560px;
  }
}

.dn-close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
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

.dn-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 40px 24px 18px;
  text-align: center;
}
.dn-hero-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: var(--radius-pill);
  background: rgb(var(--color-error-strong-rgb), 0.12);
  border: 1px solid rgb(var(--color-error-strong-rgb), 0.25);
}
.dn-hero-heart {
  color: var(--color-error-strong);
  animation: dn-heart-pulse 1.1s ease-in-out infinite;
  filter: drop-shadow(0 0 12px rgb(var(--color-error-strong-rgb), 0.6));
  transform-origin: center;
  transform-box: fill-box;
}
.dn-hero-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-extrabold);
  color: var(--text-primary);
  letter-spacing: 0.2px;
}

.dn-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px 24px 28px;
}
.dn-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* The divider only makes sense when the instance block follows the
   MediaKeeper section (admin view). On its own (regular user) it would be
   an orphan line under the hero. */
.dn-section--instance:not(:first-child) {
  padding-top: 22px;
  border-top: 1px solid var(--border-default);
}
.dn-section-title,
.dn-how {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.dn-how {
  margin-top: 4px;
}
.dn-section-title {
  text-align: center;
}
.dn-section-title::after {
  content: '';
  display: block;
  width: 200px;
  max-width: 70%;
  height: 1px;
  margin: 12px auto 0;
  border-radius: var(--radius-pill);
  background: rgb(var(--accent-rgb), 0.55);
}
.dn-intro {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--text-secondary);
  /* Preserve the blank line between the intro paragraphs (\n\n in i18n). */
  white-space: pre-line;
}
/* Operator's appeal — set apart as a soft card with an accent edge so the
   regular-user view (instance block only) feels designed, not bare text. */
.dn-quote {
  margin: 0;
  padding: 14px 16px;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-subtle);
  background: var(--surface-1);
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--text-secondary);
}
/* Prose styling for the operator's rich-text message (v-html). */
.dn-quote :deep(:first-child) {
  margin-top: 0;
}
.dn-quote :deep(:last-child) {
  margin-bottom: 0;
}
.dn-quote :deep(p) {
  margin: 0 0 0.6em;
}
.dn-quote :deep(h2),
.dn-quote :deep(h3) {
  margin: 0.7em 0 0.3em;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.dn-quote :deep(ul),
.dn-quote :deep(ol) {
  margin: 0.3em 0;
  padding-left: 1.3em;
}
.dn-quote :deep(li) {
  margin: 0.15em 0;
}
.dn-quote :deep(a) {
  color: var(--accent-300);
}
.dn-thanks {
  margin: 10px 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--border-default);
  text-align: center;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

/* Support call-to-action — an elevated card row: coloured icon chip,
   stacked label + hint, and a trailing arrow that nudges on hover. */
.dn-cta {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 64px;
  padding: 12px 16px;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-default);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  text-decoration: none;
  transition:
    transform var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}
.dn-cta-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-pill);
  background: rgb(var(--accent-rgb), 0.16);
  color: var(--accent-300);
}
.dn-cta-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  text-align: left;
}
.dn-cta-label {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
}
.dn-cta-sub {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  color: var(--text-muted);
}
.dn-cta-arrow {
  flex-shrink: 0;
  opacity: 0.45;
  transition:
    transform var(--duration-fast) var(--ease-out),
    opacity var(--duration-fast) var(--ease-out);
}
@media (hover: hover) {
  .dn-cta:hover {
    transform: translateY(-2px);
    background: var(--surface-3);
    border-color: var(--border-hover);
    box-shadow: var(--shadow-lg);
  }
  .dn-cta:hover .dn-cta-arrow {
    opacity: 1;
    transform: translate(2px, -2px);
  }
}
.dn-cta:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgb(var(--accent-rgb), 0.45);
}

/* Channel-specific icon tints (secondary cards). */
.dn-cta--sponsor .dn-cta-icon {
  background: rgb(var(--color-error-strong-rgb), 0.16);
  color: var(--color-error-strong);
}
.dn-cta--star .dn-cta-icon {
  background: rgb(var(--color-warning-rgb), 0.16);
  color: var(--color-warning);
}

/* Primary card — accent gradient, white content + chip. */
.dn-cta--primary {
  border-color: transparent;
  background: linear-gradient(135deg, var(--accent-500), var(--accent-600));
  color: var(--color-on-accent);
  box-shadow: 0 10px 28px rgb(var(--accent-rgb), 0.4);
}
.dn-cta--primary .dn-cta-icon {
  background: rgb(255, 255, 255, 0.18);
  color: var(--color-on-accent);
}
.dn-cta--primary .dn-cta-sub {
  color: rgb(255, 255, 255, 0.82);
}
@media (hover: hover) {
  .dn-cta--primary:hover {
    background: linear-gradient(135deg, var(--accent-400), var(--accent-500));
    border-color: transparent;
  }
}

@keyframes dn-heart-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  15% {
    transform: scale(1.25);
  }
  30% {
    transform: scale(1);
  }
  45% {
    transform: scale(1.18);
  }
  60% {
    transform: scale(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .dn-hero-heart {
    animation: none;
  }
  .dn-cta,
  .dn-cta-arrow {
    transition: none;
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
