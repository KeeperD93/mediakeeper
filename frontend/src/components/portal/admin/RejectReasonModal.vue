<template>
  <Teleport to="body">
    <transition name="rrm-fade">
      <div
        v-if="open"
        class="rrm-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('portal.admin.req.rejectReasonTitle')"
        @click.self="cancel"
        @keydown.esc="cancel"
      >
        <div class="rrm-panel" tabindex="-1">
          <header class="rrm-header">
            <h2 class="rrm-title">{{ $t('portal.admin.req.rejectReasonTitle') }}</h2>
            <button
              type="button"
              class="rrm-close"
              :aria-label="$t('common.close')"
              @click="cancel"
            >
              <X :size="14" />
            </button>
          </header>

          <p v-if="mediaTitle" class="rrm-media">« {{ mediaTitle }} »</p>

          <form class="rrm-form" @submit.prevent="confirm">
            <label class="rrm-field">
              <span class="rrm-field-label">{{ $t('portal.admin.req.rejectReasonLabel') }}</span>
              <textarea
                ref="taRef"
                v-model="reason"
                class="rrm-textarea"
                rows="4"
                maxlength="500"
                :placeholder="$t('portal.admin.req.rejectReasonPlaceholder')"
              />
            </label>
            <p class="rrm-hint">{{ $t('portal.admin.req.rejectReasonHint') }}</p>

            <div class="rrm-actions">
              <button type="button" class="rrm-btn rrm-btn-ghost" @click="cancel">
                {{ $t('common.cancel') }}
              </button>
              <button type="submit" class="rrm-btn rrm-btn-reject">
                {{ $t('portal.admin.reject') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  mediaTitle: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'cancel'])

const reason = ref('')
const taRef = ref(null)

watch(
  () => props.open,
  async v => {
    if (v) {
      reason.value = ''
      await nextTick()
      taRef.value?.focus()
    }
  },
)

function cancel() {
  emit('cancel')
}
function confirm() {
  emit('confirm', reason.value.trim() || null)
}
</script>

<style scoped>
.rrm-overlay {
  position: fixed;
  inset: 0;
  z-index: 9920;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgb(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}
@media (min-width: 768px) {
  .rrm-overlay {
    align-items: center;
  }
}

.rrm-panel {
  width: 100%;
  max-width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  background: var(--bg-primary);
  color: #fff;
  border: 1px solid var(--portal-border-default);
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  padding: 20px 20px calc(20px + env(safe-area-inset-bottom, 0px));
  outline: none;
}
@media (min-width: 768px) {
  .rrm-panel {
    width: min(520px, 92vw);
    border-radius: var(--radius-card);
  }
}

.rrm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.rrm-title {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  margin: 0;
}
.rrm-close {
  min-height: 44px;
  min-width: 44px;
  border: none;
  background: transparent;
  color: #fff;
  font-size: var(--portal-text-xl);
  line-height: var(--portal-lh-tight);
  cursor: pointer;
  border-radius: var(--radius-btn);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .rrm-close:hover {
    background: var(--portal-surface-4);
  }
}

.rrm-media {
  font-size: var(--portal-text-sm);
  color: rgb(255, 255, 255, 0.65);
  margin: 0 0 14px;
  font-style: italic;
}

.rrm-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rrm-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rrm-field-label {
  font-size: var(--portal-text-xs);
  color: rgb(255, 255, 255, 0.75);
  font-weight: var(--portal-font-medium);
}

.rrm-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--radius-input);
  background: var(--portal-surface-2);
  border: 1px solid rgb(255, 255, 255, 0.1);
  color: #fff;
  font: inherit;
  resize: vertical;
  min-height: 100px;
}
.rrm-textarea:focus {
  outline: none;
  border-color: var(--accent-500);
  box-shadow: 0 0 0 3px rgb(var(--accent-rgb), 0.22);
}

.rrm-hint {
  font-size: var(--portal-text-xs);
  color: rgb(255, 255, 255, 0.5);
  margin: 0;
}

.rrm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.rrm-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: var(--radius-btn);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: var(--portal-font-bold);
  -webkit-tap-highlight-color: transparent;
}
.rrm-btn-ghost {
  background: transparent;
  color: #fff;
  border-color: rgb(255, 255, 255, 0.14);
}
.rrm-btn-reject {
  background: rgb(180, 83, 9, 0.9);
  color: #fff;
}
@media (hover: hover) {
  .rrm-btn-ghost:hover {
    background: var(--portal-surface-3);
  }
  .rrm-btn-reject:hover {
    background: rgb(180, 83, 9, 1);
  }
}

.rrm-fade-enter-active,
.rrm-fade-leave-active {
  transition: opacity 180ms ease;
}
.rrm-fade-enter-from,
.rrm-fade-leave-to {
  opacity: 0;
}
.rrm-fade-enter-active .rrm-panel,
.rrm-fade-leave-active .rrm-panel {
  transition: transform var(--portal-dur-base) ease;
}
.rrm-fade-enter-from .rrm-panel,
.rrm-fade-leave-to .rrm-panel {
  transform: translateY(16px);
}
</style>
