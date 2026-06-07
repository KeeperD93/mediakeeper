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

import '@/assets/styles/donation-overlay.css'

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

// The operator message is sanitised HTML (bleach server-side, with empty
// editor content like "<p></p>" already normalised to ""). A non-empty
// value is therefore real content; DOMPurify re-purifies before v-html as
// defence in depth.
const messageHtml = computed(() => {
  const raw = props.donation?.message || ''
  return raw ? DOMPurify.sanitize(raw) : ''
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

<!-- Styles externalised to assets/styles/donation-overlay.css -->
