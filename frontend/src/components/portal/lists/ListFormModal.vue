<template>
  <Teleport to="body">
    <transition name="lfm-fade">
      <div
        v-if="open"
        class="lfm-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        @click.self="close"
        @keydown.esc="close"
      >
        <div class="lfm-panel mk-modal-sheet-panel" tabindex="-1">
          <div class="lfm-header">
            <h2 class="lfm-title">{{ title }}</h2>
            <button class="lfm-close" type="button" :aria-label="$t('common.close')" @click="close"><X :size="14" /></button>
          </div>

          <div class="lfm-body">
            <label class="lfm-label">{{ $t('portal.lists.form.name') }}</label>
            <input
              v-model="local.name"
              class="lfm-input"
              maxlength="200"
              :placeholder="$t('portal.lists.form.namePlaceholder')"
            />

            <label class="lfm-label">{{ $t('portal.lists.form.privacyLabel') }}</label>
            <div class="lfm-pill-row">
              <button
                v-for="p in privacyOptions" :key="p"
                type="button"
                class="lfm-pill"
                :class="{ 'lfm-pill--active': local.privacy === p }"
                @click="local.privacy = p"
              >{{ $t(`portal.lists.privacy.${p}`) }}</button>
            </div>

            <label class="lfm-label">{{ $t('portal.lists.form.contentTypeLabel') }}</label>
            <div class="lfm-pill-row">
              <button
                v-for="c in contentTypeOptions" :key="c"
                type="button"
                class="lfm-pill"
                :class="{ 'lfm-pill--active': local.content_type === c }"
                @click="local.content_type = c"
              >{{ $t(`portal.lists.contentType.${c}`) }}</button>
            </div>

            <label class="lfm-label">{{ $t('portal.lists.form.descriptionPlaceholder') }}</label>
            <textarea
              v-model="local.description"
              class="lfm-input"
              maxlength="1000"
              rows="3"
              :placeholder="$t('portal.lists.form.descriptionPlaceholder')"
            />
          </div>

          <div class="lfm-footer">
            <button type="button" class="lfm-btn lfm-btn--secondary" @click="close">
              {{ $t('portal.lists.form.cancel') }}
            </button>
            <button
              type="button"
              class="lfm-btn lfm-btn--primary"
              :disabled="!canSubmit"
              @click="submit"
            >{{ $t('portal.lists.form.save') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  initial: { type: Object, default: () => ({}) },
  mode: { type: String, default: 'create' },
})
const emit = defineEmits(['close', 'submit'])

const { t } = useI18n()

const privacyOptions = ['private', 'public_readonly', 'collaborative']
const contentTypeOptions = ['mixed', 'movies', 'series', 'documentaries']

const local = reactive({
  name: '',
  privacy: 'private',
  content_type: 'mixed',
  description: '',
  genres: [],
})

watch(() => props.initial, (v) => {
  local.name = v?.name || ''
  local.privacy = v?.privacy || 'private'
  local.content_type = v?.content_type || 'mixed'
  local.description = v?.description || ''
  local.genres = Array.isArray(v?.genres) ? [...v.genres] : []
}, { immediate: true, deep: true })

const canSubmit = computed(() => (local.name || '').trim().length > 0)

const title = computed(() =>
  props.mode === 'edit'
    ? t('portal.lists.form.edit')
    : t('portal.lists.form.create'),
)

function close() {
  emit('close')
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', { ...local })
}
</script>

<style scoped>
.lfm-overlay { z-index: 9999; }
.lfm-panel {
  display: flex; flex-direction: column;
  background: var(--bg-primary);
  border: .5px solid var(--portal-border-default);
  outline: none;
}
@media (min-width: 768px) { .lfm-panel { max-width: 520px; max-height: 82vh; } }

.lfm-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px 12px;
}
.lfm-title { font-size: var(--portal-text-md); font-weight: var(--portal-font-bold); color: var(--text-primary); margin: 0; }
.lfm-close {
  width: 44px; height: 44px; min-width: 44px; min-height: 44px;
  border: none; border-radius: var(--radius-btn);
  background: var(--portal-surface-2); color: var(--text-muted);
  cursor: pointer; font-size: var(--portal-text-md);
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) { .lfm-close:hover { background: var(--portal-surface-4); color: var(--text-primary); } }

.lfm-body { flex: 1; min-height: 0; overflow-y: auto; padding: 0 20px 16px; }
.lfm-label {
  display: block; font-size: var(--portal-text-xs); font-weight: var(--portal-font-bold);
  color: var(--portal-text-secondary); text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps); margin: 14px 0 6px;
}
.lfm-input {
  width: 100%; padding: 10px 12px;
  border-radius: var(--radius-input);
  border: 1px solid var(--portal-border-default);
  background: rgba(255,255,255,.03);
  color: var(--text-primary); font-size: var(--portal-text-sm); font-family: inherit;
}
.lfm-input:focus { outline: 2px solid rgba(var(--accent-rgb), .4); outline-offset: 1px; }

.lfm-pill-row { display: flex; flex-wrap: wrap; gap: 6px; }
.lfm-pill {
  padding: 7px 12px; min-height: 34px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--portal-border-default);
  background: transparent; color: var(--text-secondary);
  font-size: var(--portal-text-xs); font-weight: var(--portal-font-medium);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: all var(--portal-dur-fast);
}
.lfm-pill--active {
  border-color: var(--accent-500);
  background: rgba(var(--accent-rgb), .14);
  color: var(--accent-300);
}
@media (hover: hover) {
  .lfm-pill:hover:not(.lfm-pill--active) { border-color: rgba(255,255,255,.2); }
}

.lfm-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 14px 20px;
  border-top: .5px solid rgba(255,255,255,.05);
}
.lfm-btn {
  padding: 10px 18px; min-height: 44px;
  border-radius: var(--radius-btn); border: none;
  font-size: var(--portal-text-sm); font-weight: var(--portal-font-medium); cursor: pointer;
  font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}
.lfm-btn--secondary {
  background: transparent; color: var(--text-secondary);
  border: 1px solid rgba(255,255,255,.1);
}
.lfm-btn--primary { background: var(--accent-600); color: #fff; }
.lfm-btn--primary:disabled { opacity: .45; cursor: not-allowed; }
@media (hover: hover) {
  .lfm-btn--primary:hover:not(:disabled) { background: var(--accent-500); }
  .lfm-btn--secondary:hover { border-color: rgba(255,255,255,.25); color: var(--text-primary); }
}

.lfm-fade-enter-active { transition: all .22s ease; }
.lfm-fade-leave-active { transition: all .18s ease; }
.lfm-fade-enter-from, .lfm-fade-leave-to { opacity: 0; }
.lfm-fade-enter-from .lfm-panel { transform: translateY(12px) scale(.97); }
.lfm-fade-leave-to .lfm-panel { transform: translateY(6px) scale(.98); }
</style>
