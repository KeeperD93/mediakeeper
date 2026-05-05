<template>
  <Teleport to="body">
    <transition name="wn-fade">
      <div
        v-if="visible"
        class="wn-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="dismiss"
      >
        <div
          ref="panelRef"
          class="wn-modal mk-modal-sheet-panel"
          tabindex="-1"
          @keydown="handleModalKeydown"
        >
          <div class="wn-header">
            <div class="wn-icon-wrap">
              <Lightbulb class="wn-icon" :size="28" :stroke-width="1.5" />
            </div>
            <div>
              <h2 :id="titleId" class="wn-title">{{ $t('changelog.whatsNew') }}</h2>
              <span class="wn-version">v{{ latestVersion?.version }}</span>
            </div>
            <button
              class="wn-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="dismiss"
            >
              <X :size="16" />
            </button>
          </div>

          <div class="wn-body">
            <div v-for="(items, cat) in latestVersion?.categories" :key="cat" class="wn-category">
              <div class="wn-cat-label" :class="'wn-cat-' + cat.toLowerCase()">
                <span class="wn-cat-dot" />
                {{ $t('changelog.cat.' + cat.toLowerCase()) }}
              </div>
              <ul class="wn-items">
                <li v-for="(item, i) in items.slice(0, 5)" :key="i">{{ item }}</li>
                <li v-if="items.length > 5" class="wn-more">
                  {{ $t('changelog.andMore', { count: items.length - 5 }) }}
                </li>
              </ul>
            </div>
          </div>

          <div class="wn-footer">
            <button type="button" class="wn-btn-secondary" @click="goToChangelog">
              {{ $t('changelog.viewFull') }}
            </button>
            <button type="button" class="wn-btn-primary" @click="dismiss">
              {{ $t('changelog.gotIt') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { Lightbulb, X } from 'lucide-vue-next'

const { apiGet, apiPost } = useApi()
const router = useRouter()
const { locale } = useI18n()

const visible = ref(false)
const latestVersion = ref(null)
const panelRef = ref(null)
const titleId = 'mk-whats-new-title'
let lastFocusedElement = null

onMounted(async () => {
  try {
    const check = await apiGet('/api/changelog/check')
    if (!check?.has_new) return
    const localSeen = localStorage.getItem('mk_changelog_seen')
    if (localSeen === check.current_version) return
    const data = await apiGet(`/api/changelog/?limit=1&lang=${locale.value}`)
    if (data?.versions?.length) {
      latestVersion.value = data.versions[0]
      visible.value = true
    }
  } catch {
    /* silent: modal is opportunistic, skip on fetch failure */
  }
})

watch(visible, async isOpen => {
  if (isOpen) {
    lastFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    panelRef.value?.focus?.()
    return
  }
  if (lastFocusedElement) {
    await nextTick()
    lastFocusedElement.focus?.()
    lastFocusedElement = null
  }
})

onBeforeUnmount(() => {
  if (lastFocusedElement) lastFocusedElement.focus?.()
})

async function dismiss() {
  visible.value = false
  try {
    const res = await apiPost('/api/changelog/seen', {})
    if (res?.version) localStorage.setItem('mk_changelog_seen', res.version)
  } catch {
    /* silent: seen-marker is best-effort */
  }
}

function goToChangelog() {
  dismiss()
  router.push('/changelog')
}

function handleModalKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    dismiss()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = panelRef.value?.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )
  const elements = Array.from(focusable || []).filter(el => el.offsetParent !== null)
  if (elements.length === 0) {
    event.preventDefault()
    panelRef.value?.focus?.()
    return
  }
  const currentIndex = elements.indexOf(document.activeElement)
  if (event.shiftKey) {
    if (currentIndex <= 0) {
      event.preventDefault()
      elements.at(-1)?.focus()
    }
    return
  }
  if (currentIndex === -1 || currentIndex === elements.length - 1) {
    event.preventDefault()
    elements[0]?.focus()
  }
}
</script>

<style scoped>
/* Layout delegated to .mk-modal-sheet — only component-specific visuals here */
.wn-overlay {
  z-index: 9999;
}
.wn-modal {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 0.5px solid var(--border-strong);
}
@media (min-width: 768px) {
  .wn-modal {
    max-height: 80vh;
  }
}

.wn-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 14px;
}
.wn-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-card);
  background: rgb(var(--accent-rgb), 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wn-icon {
  color: var(--accent-400);
}
.wn-title {
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
}
.wn-version {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--accent-400);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
}
.wn-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--surface-2);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}
.wn-close:hover {
  background: rgb(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.wn-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 16px;
}
.wn-category {
  margin-bottom: 14px;
}
.wn-category:last-child {
  margin-bottom: 0;
}
.wn-cat-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  margin-bottom: 6px;
}
.wn-cat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.wn-cat-added .wn-cat-dot {
  background: var(--color-success);
}
.wn-cat-added {
  color: var(--color-success);
}
.wn-cat-fixed .wn-cat-dot {
  background: var(--color-info);
}
.wn-cat-fixed {
  color: var(--color-info);
}
.wn-cat-changed .wn-cat-dot {
  background: var(--color-warning);
}
.wn-cat-changed {
  color: var(--color-warning);
}
.wn-cat-removed .wn-cat-dot {
  background: var(--color-error);
}
.wn-cat-removed {
  color: var(--color-error);
}

.wn-items {
  list-style: none;
  padding: 0;
  margin: 0;
}
.wn-items li {
  padding: 3px 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--lh-normal);
}
.wn-items li::before {
  content: '→ ';
  color: var(--text-muted);
}
.wn-more {
  font-style: italic;
  color: var(--text-muted) !important;
}
.wn-more::before {
  content: '' !important;
}

.wn-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 0.5px solid rgb(255, 255, 255, 0.05);
}
.wn-btn-secondary {
  padding: 8px 16px;
  border-radius: var(--radius-btn);
  border: 0.5px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--duration-fast);
}
.wn-btn-secondary:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}
.wn-btn-primary {
  padding: 8px 20px;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent-600);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--duration-fast);
}
.wn-btn-primary:hover {
  background: var(--accent-500);
}

.wn-fade-enter-active {
  transition: all 0.25s ease;
}
.wn-fade-leave-active {
  transition: all var(--duration-base) ease;
}
.wn-fade-enter-from,
.wn-fade-leave-to {
  opacity: 0;
}
.wn-fade-enter-from .wn-modal {
  transform: translateY(16px) scale(0.97);
}
.wn-fade-leave-to .wn-modal {
  transform: translateY(8px) scale(0.98);
}
</style>
