<template>
  <Teleport to="body">
    <transition name="pt-dpb">
      <div v-if="visible" class="pt-dpb" role="status" :style="{ top: `${navOffset}px` }">
        <div class="pt-dpb-inner">
          <AlertTriangle :size="18" class="pt-dpb-icon" />
          <span class="pt-dpb-text">
            <i18n-t keypath="portal.privacy.banner.message" tag="span">
              <template #date>
                <strong class="pt-dpb-date">{{ formattedDate }}</strong>
              </template>
            </i18n-t>
          </span>
          <button type="button" class="pt-dpb-cancel" :disabled="cancelling" @click="onCancel">
            {{
              cancelling
                ? $t('portal.privacy.banner.cancelling')
                : $t('portal.privacy.banner.cancel')
            }}
          </button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useGdprUser } from '@/composables/portal/useGdprUser'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

// Sits flush against the portal nav's bottom edge. Same measurement
// strategy as EventBanner — measure live so a responsive nav (mobile
// collapse, solid mode border) does not require a hard-coded offset.
const { gdpr, refreshAuth } = usePortalAuth()
const { cancelDeletion } = useGdprUser()
const { t, locale } = useI18n()
const { showToast } = useToast()

const navOffset = ref(0)
const cancelling = ref(false)

const visible = computed(() => !!gdpr.value?.pending_deletion_at)

const formattedDate = computed(() => {
  const iso = gdpr.value?.pending_deletion_at
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(locale.value, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
})

function measureNav() {
  const nav = document.querySelector('.pt-nav')
  navOffset.value = nav ? Math.round(nav.getBoundingClientRect().bottom) : 0
}

let navObserver = null

onMounted(() => {
  measureNav()
  window.addEventListener('resize', measureNav)
  window.addEventListener('scroll', measureNav, { passive: true })
  const nav = document.querySelector('.pt-nav')
  if (nav && typeof ResizeObserver !== 'undefined') {
    navObserver = new ResizeObserver(measureNav)
    navObserver.observe(nav)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', measureNav)
  window.removeEventListener('scroll', measureNav)
  if (navObserver) navObserver.disconnect()
})

async function onCancel() {
  if (cancelling.value) return
  cancelling.value = true
  try {
    await cancelDeletion()
    await refreshAuth()
    showToast(t('portal.privacy.banner.cancelled'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.privacy.banner.cancelFailed'), TOAST_TYPE.ERR)
  } finally {
    cancelling.value = false
  }
}
</script>

<style scoped>
.pt-dpb {
  position: fixed;
  left: 0;
  right: 0;
  z-index: 100; /* one above EventBanner so the user always sees it */
  background: rgb(180, 83, 9, 0.92);
  color: #fff;
  border-top: 1px solid rgb(255, 255, 255, 0.15);
  border-bottom: 1px solid rgb(255, 255, 255, 0.15);
  box-shadow: 0 2px 12px rgb(0, 0, 0, 0.35);
  font-size: var(--portal-text-sm);
}
.pt-dpb-inner {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 1rem;
}
.pt-dpb-icon {
  flex: 0 0 auto;
  color: #fef3c7;
}
.pt-dpb-text {
  flex: 1 1 auto;
  line-height: 1.4;
}
.pt-dpb-date {
  font-weight: var(--portal-font-bold);
  white-space: nowrap;
}
.pt-dpb-cancel {
  flex: 0 0 auto;
  background: rgb(255, 255, 255, 0.18);
  color: #fff;
  border: 1px solid rgb(255, 255, 255, 0.4);
  border-radius: 999px;
  padding: 0.3rem 0.85rem;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  letter-spacing: var(--portal-tracking-wide);
  cursor: pointer;
  transition: background 0.18s ease;
}
.pt-dpb-cancel:hover:not(:disabled) {
  background: rgb(255, 255, 255, 0.28);
}
.pt-dpb-cancel:disabled {
  opacity: 0.6;
  cursor: progress;
}

.pt-dpb-enter-active,
.pt-dpb-leave-active {
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
}
.pt-dpb-enter-from,
.pt-dpb-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

@media (max-width: 640px) {
  .pt-dpb-inner {
    flex-wrap: wrap;
    padding: 0.45rem 0.75rem;
  }
  .pt-dpb-text {
    flex-basis: 100%;
    order: 2;
  }
  .pt-dpb-cancel {
    order: 3;
    margin-left: auto;
  }
}
</style>
