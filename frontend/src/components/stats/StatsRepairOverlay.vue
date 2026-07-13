<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="open" class="rlo-overlay" @click.self="onClose">
        <div
          ref="panelRef"
          class="rlo-modal"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
        >
          <div
            v-if="running"
            class="rlo-progress"
            role="progressbar"
            :aria-label="$t('stats.repair.running')"
          >
            <span class="rlo-progress-bar" />
          </div>

          <div class="rlo-header">
            <RefreshCw :size="18" class="rlo-ico" :class="{ 'rlo-spin': running }" />
            <h2 :id="titleId" class="rlo-title">{{ $t('stats.repair.title') }}</h2>
            <button
              ref="closeBtnRef"
              class="rlo-close"
              :aria-label="$t('common.close')"
              :disabled="running"
              @click="onClose"
            >
              <X :size="16" />
            </button>
          </div>

          <div class="rlo-body">
            <p v-if="running" class="rlo-note">{{ $t('stats.repair.running') }}</p>
            <p v-else-if="error" class="rlo-note rlo-err-note">{{ error }}</p>

            <template v-else-if="result">
              <div class="rlo-summary">
                <span class="rlo-chip rlo-ok">
                  {{ result.migrated }} {{ $t('stats.repair.migrated') }}
                </span>
                <span class="rlo-chip rlo-warn">
                  {{ result.unresolved }} {{ $t('stats.repair.unresolved') }}
                </span>
                <span v-if="result.errors" class="rlo-chip rlo-err">
                  {{ result.errors }} {{ $t('stats.repair.errors') }}
                </span>
              </div>

              <p v-if="!result.candidates" class="rlo-empty">{{ $t('stats.repair.empty') }}</p>

              <section v-if="migrated.length" class="rlo-section">
                <h3 class="rlo-sec-title rlo-ok">
                  {{ $t('stats.repair.migratedTitle') }} ({{ migrated.length }})
                </h3>
                <div v-for="d in migrated" :key="d.item_id" class="rlo-row">
                  <span class="rlo-item">{{ d.item_name || d.item_id }}</span>
                  <ArrowRight :size="13" class="rlo-arrow" />
                  <span class="rlo-lib">{{ d.library_name }}</span>
                </div>
              </section>

              <section v-if="unresolved.length" class="rlo-section">
                <h3 class="rlo-sec-title rlo-warn">
                  {{ $t('stats.repair.unresolvedTitle') }} ({{ unresolved.length }})
                </h3>
                <p class="rlo-sec-hint">{{ $t('stats.repair.unresolvedHint') }}</p>
                <div v-for="d in unresolved" :key="d.item_id" class="rlo-row rlo-row-col">
                  <span class="rlo-item">{{ d.item_name || d.item_id }}</span>
                  <span class="rlo-diag" :class="{ 'rlo-diag-flag': !hasCollection(d) }">
                    {{ ancestryText(d) }}
                  </span>
                </div>
              </section>

              <section v-if="errored.length" class="rlo-section">
                <h3 class="rlo-sec-title rlo-err">
                  {{ $t('stats.repair.errorsTitle') }} ({{ errored.length }})
                </h3>
                <div v-for="d in errored" :key="d.item_id" class="rlo-row">
                  <span class="rlo-item">{{ d.item_name || d.item_id }}</span>
                </div>
              </section>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { ArrowRight, RefreshCw, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  running: { type: Boolean, default: false },
  result: { type: Object, default: null },
  error: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const panelRef = ref(null)
const closeBtnRef = ref(null)
const titleId = useId()
const isOpen = computed(() => props.open)

function onClose() {
  if (props.running) return // don't let the user dismiss a run in progress
  emit('close')
}

useFocusTrap({
  active: isOpen,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: onClose,
})

const details = computed(() => props.result?.details || [])
const migrated = computed(() => details.value.filter(d => d.status === 'migrated'))
const unresolved = computed(() => details.value.filter(d => d.status === 'unresolved'))
const errored = computed(() => details.value.filter(d => d.status === 'error'))

function hasCollection(d) {
  return (d.ancestors || []).some(a => a.type === 'CollectionFolder')
}
function ancestryText(d) {
  const chain = (d.ancestors || []).map(a => `${a.type}: ${a.name}`).join('  ›  ')
  return chain || t('stats.repair.noAncestry')
}
</script>

<style scoped>
.rlo-overlay {
  position: fixed;
  inset: 0;
  z-index: 9990;
  background: rgb(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.rlo-modal {
  position: relative;
  width: 640px;
  max-width: 100%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--mk-chrome-bg);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-card);
}
.rlo-progress {
  height: 3px;
  background: rgb(var(--accent-rgb), 0.15);
  overflow: hidden;
  flex-shrink: 0;
}
.rlo-progress-bar {
  display: block;
  height: 100%;
  width: 40%;
  background: var(--accent-500);
  border-radius: var(--radius-pill);
  animation: rlo-indeterminate 1.1s ease-in-out infinite;
}
@keyframes rlo-indeterminate {
  0% {
    transform: translateX(-110%);
  }
  100% {
    transform: translateX(360%);
  }
}
.rlo-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.rlo-ico {
  color: var(--accent-500);
  flex-shrink: 0;
}
.rlo-title {
  flex: 1;
  min-width: 0;
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
}
.rlo-close {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-btn);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--duration-fast);
}
.rlo-close:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}
.rlo-body {
  padding: 14px 18px 18px;
  overflow-y: auto;
}
.rlo-note {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 6px 0;
}
.rlo-err-note {
  color: var(--color-error);
}
.rlo-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.rlo-chip {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
}
.rlo-ok {
  color: var(--color-success);
}
.rlo-warn {
  color: var(--color-warning);
}
.rlo-err {
  color: var(--color-error);
}
.rlo-chip.rlo-ok {
  background: rgb(var(--color-success-rgb), 0.12);
}
.rlo-chip.rlo-warn {
  background: rgb(var(--color-warning-rgb), 0.12);
}
.rlo-chip.rlo-err {
  background: rgb(var(--color-error-rgb), 0.12);
}
.rlo-empty {
  font-size: var(--text-sm);
  color: var(--text-muted);
  padding: 8px 0;
}
.rlo-section {
  margin-top: 14px;
}
.rlo-sec-title {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin: 0 0 8px;
}
.rlo-sec-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: 0 0 8px;
  line-height: var(--lh-normal);
}
.rlo-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--radius-input);
  border-bottom: 0.5px solid var(--border-default);
}
.rlo-row:last-child {
  border-bottom: none;
}
.rlo-row-col {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.rlo-item {
  font-size: var(--text-sm);
  color: var(--text-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.rlo-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}
.rlo-lib {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-success);
}
.rlo-diag {
  font-size: var(--text-2xs);
  font-family: 'Space Mono', monospace;
  color: var(--text-secondary);
  overflow-wrap: break-word;
  line-height: var(--lh-normal);
}
.rlo-diag-flag {
  color: var(--color-warning);
}
.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity var(--duration-base);
}
.sub-fade-enter-from,
.sub-fade-leave-to {
  opacity: 0;
}
@media (min-width: 768px) {
  .rlo-close {
    width: 32px;
    height: 32px;
  }
}
@media (hover: hover) {
  .rlo-close:not(:disabled):hover {
    background: rgb(var(--color-error-rgb), 0.1);
    color: var(--color-error);
  }
}
@media (prefers-reduced-motion: reduce) {
  .rlo-progress-bar {
    animation: none;
    width: 100%;
    opacity: 0.6;
  }
  .rlo-spin {
    animation: none;
  }
}
.rlo-spin {
  animation: rlo-spin 1s linear infinite;
}
@keyframes rlo-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
