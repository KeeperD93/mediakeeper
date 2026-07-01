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
        <form ref="panelRef" class="fbk-panel" @submit.prevent="submit">
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
              <input v-model="title" type="text" maxlength="120" required />
            </label>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.descField') }} *</span>
              <textarea v-model="description" rows="4" maxlength="1500" required />
            </label>

            <label class="fbk-field">
              <span class="fbk-flabel">{{ $t('feedback.modal.reproField') }}</span>
              <textarea v-model="reproduction" rows="2" maxlength="500" />
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
                <option v-for="r in RES_PRESETS" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
                <option value="__custom__">{{ $t('feedback.modal.resolutionOther') }}</option>
              </select>
            </label>
            <input
              v-if="resolutionChoice === '__custom__'"
              v-model="resolutionCustom"
              type="text"
              maxlength="40"
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
import { computed, reactive, ref, toRef, watch, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { useApi, resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { TOAST_TYPE } from '@/constants/toast'
import {
  FEEDBACK_TYPES,
  FEEDBACK_PLATFORMS,
  FEEDBACK_TAGS,
  FEEDBACK_MAX_CHARS,
} from '@/constants/feedback'
import '@/assets/styles/feedback-modal.css'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close'])
const titleId = useId()

const { t } = useI18n()
const { apiPost } = useApi()
const { showToast } = useToast()

const RES_PRESETS = [
  { label: 'Full HD', value: '1920x1080' },
  { label: '2K', value: '2560x1440' },
  { label: '4K', value: '3840x2160' },
]
// Roughly the fixed block overhead (delimiters + labels + meta line) so the
// counter stays conservative vs the backend's 2000-char truncation.
const OVERHEAD = 170

const type = ref('bug')
const title = ref('')
const description = ref('')
const reproduction = ref('')
const platforms = reactive({ desktop: false, mobile: false })
const resolutionChoice = ref('')
const resolutionCustom = ref('')
const selectedTags = ref(new Set())
const anonymous = ref(false)
const busy = ref(false)
const panelRef = ref(null)
const closeBtnRef = ref(null)

const resolution = computed(() =>
  resolutionChoice.value === '__custom__' ? resolutionCustom.value.trim() : resolutionChoice.value,
)
const platform = computed(() => {
  if (platforms.desktop && platforms.mobile) return 'both'
  if (platforms.desktop) return 'desktop'
  if (platforms.mobile) return 'mobile'
  return 'both'
})
const used = computed(
  () =>
    OVERHEAD +
    title.value.length +
    description.value.length +
    reproduction.value.length +
    resolution.value.length +
    [...selectedTags.value].join(', ').length,
)
const canSubmit = computed(
  () => !!title.value.trim() && !!description.value.trim() && used.value <= FEEDBACK_MAX_CHARS,
)

function toggleTag(tag) {
  const next = new Set(selectedTags.value)
  if (next.has(tag)) next.delete(tag)
  else next.add(tag)
  selectedTags.value = next
}

function reset() {
  type.value = 'bug'
  title.value = ''
  description.value = ''
  reproduction.value = ''
  platforms.desktop = false
  platforms.mobile = false
  resolutionChoice.value = ''
  resolutionCustom.value = ''
  selectedTags.value = new Set()
  anonymous.value = false
}

watch(
  () => props.open,
  v => {
    if (v) reset()
  },
)

async function submit() {
  if (!canSubmit.value) return
  busy.value = true
  try {
    await apiPost('/api/feedback', {
      type: type.value,
      title: title.value.trim(),
      description: description.value.trim(),
      reproduction: reproduction.value.trim(),
      platform: platform.value,
      resolution: resolution.value,
      tags: [...selectedTags.value],
      anonymous: anonymous.value,
    })
    showToast(t('feedback.modal.sent'), TOAST_TYPE.OK)
    emit('close')
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    busy.value = false
  }
}

function close() {
  if (!busy.value) emit('close')
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>
