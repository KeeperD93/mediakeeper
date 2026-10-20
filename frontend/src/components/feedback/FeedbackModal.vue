<template>
  <Teleport to="body">
    <transition name="fbk-fade">
      <div
        v-if="open"
        class="fbk-overlay"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="close"
      >
        <form ref="panelRef" class="fbk-panel" @submit.prevent="send">
          <header class="fbk-header">
            <h2 :id="titleId" class="fbk-title">{{ $t('feedback.modal.title') }}</h2>
            <button
              ref="closeBtnRef"
              type="button"
              class="fbk-close"
              :aria-label="$t('common.close')"
              @click="close"
            >
              <X :size="16" />
            </button>
          </header>

          <div class="fbk-body">
            <div class="fbk-seg" role="group" :aria-label="$t('feedback.modal.title')">
              <button
                v-for="ty in FEEDBACK_TYPES"
                :key="ty"
                type="button"
                class="fbk-seg-btn"
                :class="{ active: type === ty }"
                @click="type = ty"
              >
                {{ $t(`feedback.modal.type_${ty}`) }}
              </button>
            </div>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.titleField') }} *</span>
              <input v-model="title" type="text" :maxlength="FEEDBACK_MAX.title" required />
            </label>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.descField') }} *</span>
              <textarea
                v-model="description"
                rows="4"
                :maxlength="FEEDBACK_MAX.description"
                required
              />
            </label>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.reproField') }}</span>
              <textarea v-model="reproduction" rows="2" :maxlength="FEEDBACK_MAX.reproduction" />
            </label>

            <label v-if="showLocation" class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.pageField') }}</span>
              <select v-model="pageRoute" class="fbk-select" @change="onPageChange">
                <option value="">{{ $t('feedback.modal.locationNone') }}</option>
                <option v-for="p in FEEDBACK_PAGES" :key="p.route" :value="p.route">
                  {{ $t(p.titleKey) }}
                </option>
              </select>
            </label>

            <label v-if="showLocation && tabOptions.length" class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.ongletField') }}</span>
              <select v-model="tabId" class="fbk-select">
                <option value="">{{ $t('feedback.modal.locationNone') }}</option>
                <option v-for="tb in tabOptions" :key="tb.id" :value="tb.id">
                  {{ $t(tb.labelKey) }}
                </option>
              </select>
            </label>

            <div class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.platform') }}</span>
              <div class="fbk-chips">
                <button
                  v-for="p in FEEDBACK_PLATFORMS"
                  :key="p"
                  type="button"
                  class="fbk-chip"
                  :class="{ active: platforms[p] }"
                  :aria-pressed="platforms[p]"
                  @click="platforms[p] = !platforms[p]"
                >
                  {{ $t(`feedback.modal.platform_${p}`) }}
                </button>
              </div>
            </div>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.resolution') }}</span>
              <select v-model="resolutionChoice" class="fbk-select">
                <option value="">{{ $t('feedback.modal.resolutionNone') }}</option>
                <option v-for="r in FEEDBACK_RES_PRESETS" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
                <option :value="FEEDBACK_RES_CUSTOM">
                  {{ $t('feedback.modal.resolutionOther') }}
                </option>
              </select>
            </label>
            <input
              v-if="resolutionChoice === FEEDBACK_RES_CUSTOM"
              v-model="resolutionCustom"
              type="text"
              :maxlength="FEEDBACK_MAX.resolution"
              :aria-label="$t('feedback.modal.resolution')"
              :placeholder="$t('feedback.modal.resolutionPlaceholder')"
            />

            <div class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.tags') }}</span>
              <div class="fbk-chips">
                <button
                  v-for="tag in FEEDBACK_TAGS"
                  :key="tag"
                  type="button"
                  class="fbk-chip"
                  :class="{ active: selectedTags.has(tag) }"
                  :aria-pressed="selectedTags.has(tag)"
                  @click="toggleTag(tag)"
                >
                  {{ $t(`feedback.tags.${tag}`) }}
                </button>
              </div>
            </div>

            <label class="fbk-check">
              <input v-model="anonymous" type="checkbox" />
              <span>{{ $t('feedback.modal.anonymous') }}</span>
            </label>

            <p class="fbk-budget" :class="{ over: used > FEEDBACK_MAX_CHARS }">
              {{ $t('feedback.modal.budget', { used, max: FEEDBACK_MAX_CHARS }) }}
            </p>
          </div>

          <footer class="fbk-footer">
            <button
              v-if="canModerate"
              type="button"
              class="fbk-btn fbk-btn--ghost fbk-btn--moderate"
              @click="goModerate"
            >
              <Inbox :size="16" />
              {{ $t('feedback.modal.moderate') }}
            </button>
            <button
              type="button"
              class="fbk-btn fbk-btn--ghost fbk-btn--reset"
              :disabled="busy"
              @click="reset"
            >
              {{ $t('feedback.modal.reset') }}
            </button>
            <button type="button" class="fbk-btn fbk-btn--ghost" @click="close">
              {{ $t('common.cancel') }}
            </button>
            <button type="submit" class="fbk-btn fbk-btn--primary" :disabled="busy || !canSubmit">
              {{ $t('feedback.modal.submit') }}
            </button>
          </footer>
        </form>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, toRef, watch, useId } from 'vue'
import { useRouter } from 'vue-router'
import { X, Inbox } from 'lucide-vue-next'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useFeedbackForm } from '@/composables/useFeedbackForm'
import {
  FEEDBACK_TYPES,
  FEEDBACK_PLATFORMS,
  FEEDBACK_TAGS,
  FEEDBACK_MAX,
  FEEDBACK_MAX_CHARS,
  FEEDBACK_PAGES,
  FEEDBACK_RES_CUSTOM,
  FEEDBACK_RES_PRESETS,
} from '@/constants/feedback'
import '@/assets/styles/feedback-modal.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  endpoint: { type: String, default: '/api/feedback' },
  showLocation: { type: Boolean, default: true },
  // Reveals the "view pending reports" shortcut; gated on backoffice access
  // by the caller, since moderation is admin-only server-side.
  canModerate: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
const titleId = useId()
const router = useRouter()

const {
  type,
  title,
  description,
  reproduction,
  pageRoute,
  tabId,
  platforms,
  resolutionChoice,
  resolutionCustom,
  selectedTags,
  anonymous,
  busy,
  tabOptions,
  used,
  canSubmit,
  toggleTag,
  onPageChange,
  reset,
  prefill,
  submit,
} = useFeedbackForm({
  endpoint: () => props.endpoint,
  showLocation: () => props.showLocation,
})
const panelRef = ref(null)
const closeBtnRef = ref(null)

watch(
  () => props.open,
  v => {
    if (v) prefill()
  },
)

// Close and clear while still sending: the window fades out exactly as it was sent.
function send() {
  submit(() => {
    emit('close')
    reset()
  })
}

function close() {
  if (!busy.value) emit('close')
}

function goModerate() {
  emit('close')
  router.push('/feedback')
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>
