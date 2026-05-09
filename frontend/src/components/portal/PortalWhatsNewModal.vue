<template>
  <Teleport to="body">
    <transition name="dwn-fade">
      <div
        v-if="visible"
        class="dwn-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('portal.changelog.whatsNew')"
        @click.self="dismiss"
      >
        <div ref="panelRef" class="dwn-modal mk-modal-sheet-panel" tabindex="-1">
          <div class="dwn-header">
            <div class="dwn-icon-wrap">
              <Lightbulb class="dwn-icon" :size="28" :stroke-width="1.5" />
            </div>
            <div>
              <h2 class="dwn-title">{{ $t('portal.changelog.whatsNew') }}</h2>
              <span class="dwn-version">v{{ latestVersion?.version }}</span>
            </div>
            <button
              ref="closeBtnRef"
              class="dwn-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="dismiss"
            >
              <X :size="16" />
            </button>
          </div>

          <div class="dwn-body">
            <div v-for="(items, cat) in latestVersion?.categories" :key="cat" class="dwn-category">
              <div class="dwn-cat-label" :class="'dwn-cat-' + cat.toLowerCase()">
                <span class="dwn-cat-dot" />
                {{ $t('changelog.cat.' + cat.toLowerCase()) }}
              </div>
              <ul class="dwn-items">
                <li v-for="(item, i) in items.slice(0, 5)" :key="i">{{ item }}</li>
                <li v-if="items.length > 5" class="dwn-more">
                  {{ $t('changelog.andMore', { count: items.length - 5 }) }}
                </li>
              </ul>
            </div>
          </div>

          <div class="dwn-footer">
            <button type="button" class="dwn-btn-secondary" @click="goToChangelog">
              {{ $t('changelog.viewFull') }}
            </button>
            <button type="button" class="dwn-btn-primary" @click="dismiss">
              {{ $t('changelog.gotIt') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { Lightbulb, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  auto: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])

const { apiGet, apiPost } = useApi()
const router = useRouter()
const { locale } = useI18n()

const visible = ref(false)
const latestVersion = ref(null)
const panelRef = ref(null)
const closeBtnRef = ref(null)

async function load({ bypassCheck = false } = {}) {
  try {
    if (!bypassCheck) {
      const check = await apiGet('/api/portal/changelog/check')
      if (!check?.has_new) return false
      const localSeen = localStorage.getItem('mk_portal_changelog_seen')
      if (localSeen === check.current_version) return false
    }
    const data = await apiGet(`/api/portal/changelog/?limit=1&lang=${locale.value}`)
    if (data?.versions?.length) {
      latestVersion.value = data.versions[0]
      visible.value = true
      await nextTick()
      panelRef.value?.focus?.()
      return true
    }
  } catch {
    /* silent: modal is opportunistic, skip on fetch failure */
  }
  return false
}

async function dismiss() {
  visible.value = false
  emit('close')
  try {
    const res = await apiPost('/api/portal/changelog/seen', {})
    if (res?.version) localStorage.setItem('mk_portal_changelog_seen', res.version)
  } catch {
    /* silent: seen-marker is best-effort */
  }
}

function goToChangelog() {
  dismiss()
  router.push({ name: 'portal-changelog' })
}

watch(
  () => props.open,
  v => {
    if (v) load({ bypassCheck: true })
  },
  { immediate: false },
)

useFocusTrap({
  active: visible,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: dismiss,
})

if (props.auto) {
  load()
}
</script>

<style scoped>
.dwn-overlay {
  z-index: 9999;
}
.dwn-modal {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 0.5px solid var(--portal-border-default);
  outline: none;
}
@media (min-width: 768px) {
  .dwn-modal {
    max-height: 80vh;
  }
}

.dwn-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 14px;
}
.dwn-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-card);
  background: rgb(var(--accent-rgb), 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.dwn-icon {
  color: var(--accent-400);
}
.dwn-title {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin: 0;
}
.dwn-version {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-medium);
  color: var(--accent-400);
  font-family: var(--portal-font-mono);
}
.dwn-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--portal-surface-2);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--portal-dur-fast);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .dwn-close:hover {
    background: var(--portal-surface-4);
    color: var(--text-primary);
  }
}
@media (max-width: 767px) {
  .dwn-close {
    width: 44px;
    height: 44px;
    min-width: 44px;
    min-height: 44px;
  }
}

.dwn-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 20px 16px;
}
.dwn-category {
  margin-bottom: 14px;
}
.dwn-category:last-child {
  margin-bottom: 0;
}
.dwn-cat-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  margin-bottom: 6px;
}
.dwn-cat-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--portal-radius-circle);
  flex-shrink: 0;
}
.dwn-cat-added .dwn-cat-dot {
  background: var(--portal-color-success-light);
}
.dwn-cat-added {
  color: var(--portal-color-success-light);
}
.dwn-cat-fixed .dwn-cat-dot {
  background: var(--portal-color-info-light);
}
.dwn-cat-fixed {
  color: var(--portal-color-info-light);
}
.dwn-cat-changed .dwn-cat-dot {
  background: var(--portal-color-warning);
}
.dwn-cat-changed {
  color: var(--portal-color-warning);
}
.dwn-cat-removed .dwn-cat-dot {
  background: var(--portal-color-error-light);
}
.dwn-cat-removed {
  color: var(--portal-color-error-light);
}

.dwn-items {
  list-style: none;
  padding: 0;
  margin: 0;
}
.dwn-items li {
  padding: 3px 0;
  font-size: var(--portal-text-xs);
  color: var(--text-secondary);
  line-height: var(--portal-lh-normal);
}
.dwn-items li::before {
  content: '→ ';
  color: var(--text-muted);
}
.dwn-more {
  font-style: italic;
  color: var(--text-muted) !important;
}
.dwn-more::before {
  content: '' !important;
}

.dwn-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 0.5px solid rgb(255, 255, 255, 0.05);
}
.dwn-btn-secondary {
  padding: 10px 16px;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-regular);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--portal-dur-fast);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .dwn-btn-secondary:hover {
    border-color: var(--border-hover);
    color: var(--text-primary);
  }
}
.dwn-btn-primary {
  padding: 10px 20px;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent-600);
  color: #fff;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--portal-dur-fast);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .dwn-btn-primary:hover {
    background: var(--accent-500);
  }
}

.dwn-fade-enter-active {
  transition: all var(--portal-dur-med) ease;
}
.dwn-fade-leave-active {
  transition: all var(--portal-dur-base) ease;
}
.dwn-fade-enter-from,
.dwn-fade-leave-to {
  opacity: 0;
}
.dwn-fade-enter-from .dwn-modal {
  transform: translateY(16px) scale(0.97);
}
.dwn-fade-leave-to .dwn-modal {
  transform: translateY(8px) scale(0.98);
}
</style>
