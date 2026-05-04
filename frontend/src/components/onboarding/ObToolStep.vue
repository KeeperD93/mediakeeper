<template>
  <div class="ob-panel">
    <div class="ob-step-header">
      <div class="ob-step-icon" :style="{ background: iconBg }">
        <img
          v-if="iconSrc"
          :src="iconSrc"
          width="26"
          height="26"
          onerror="this.style.display = 'none'"
        />
        <MessageSquare v-else :size="22" :stroke-width="1.8" />
      </div>
      <div>
        <h2 class="ob-panel-title">{{ title }}</h2>
        <p class="ob-panel-desc">{{ desc }}</p>
      </div>
    </div>

    <div class="ob-form">
      <div v-if="hasUrlField" class="ob-field">
        <label class="ob-label">{{ urlLabel }}</label>
        <input v-model="model.url" class="ob-input" :placeholder="urlPlaceholder" type="url" />
      </div>
      <div class="ob-field">
        <label class="ob-label">
          {{ keyLabel }}
          <a
            v-if="keyHelpHref"
            :href="keyHelpHref"
            target="_blank"
            rel="noopener noreferrer"
            class="ob-label-link"
          >
            {{ keyHelpText }} ↗
          </a>
        </label>
        <input
          :type="inputType"
          :value="displayedApiKey"
          class="ob-input ob-mono"
          :placeholder="keyPlaceholder"
          @focus="onKeyFocus"
          @input="onKeyInput($event.target.value)"
        />
      </div>
    </div>

    <div class="ob-test-row">
      <button class="ob-test-btn" :disabled="model._testing || !canTest" @click="$emit('test')">
        <span v-if="model._testing" class="ob-spin-dark" />
        <Zap v-else :size="13" />
        {{ $t('onboarding.test') }}
      </button>
      <transition name="ob-fade">
        <span v-if="model._status" class="ob-inline-status" :class="'ob-ist-' + model._status.type">
          {{ model._status.msg }}
        </span>
      </transition>
    </div>

    <div v-if="guideChips && guideChips.length" class="ob-guide-box">
      <div class="ob-guide-title">
        <Info :size="13" />
        {{ $t('onboarding.whereToFind') }}
      </div>
      <div class="ob-guide-steps">
        <template v-for="(chip, i) in guideChips" :key="i">
          <span class="ob-guide-chip">{{ chip }}</span>
          <span v-if="i < guideChips.length - 1" class="ob-guide-arrow">→</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Info, MessageSquare, Zap } from 'lucide-vue-next'
import { safeHref } from '@/utils/safeUrl'

const model = defineModel({ type: Object, required: true })

const props = defineProps({
  title: { type: String, required: true },
  desc: { type: String, required: true },
  iconBg: { type: String, default: 'rgba(var(--accent-rgb),.1)' },
  iconSrc: { type: String, default: '' },
  hasUrlField: { type: Boolean, default: false },
  urlLabel: { type: String, default: '' },
  urlPlaceholder: { type: String, default: '' },
  keyLabel: { type: String, required: true },
  keyPlaceholder: { type: String, default: '' },
  keyHelpUrl: { type: String, default: '' },
  keyHelpText: { type: String, default: '' },
  guideChips: { type: Array, default: () => [] },
})

defineEmits(['test'])

// Tool definitions are admin-managed but the help link is rendered as
// an anchor — refuse anything outside http(s)/mailto so a poisoned
// config can never expose ``javascript:`` to operators.
const keyHelpHref = computed(() => safeHref(props.keyHelpUrl))

const secretEditing = ref(false)

const apiKeyMask = computed(() => {
  if (!model.value?._configured) return ''
  const length = Number(model.value?.api_key_length) || 0
  return '*'.repeat(Math.max(1, length))
})

const displayedApiKey = computed(() => {
  if (secretEditing.value || !model.value?._configured) return model.value.api_key || ''
  return apiKeyMask.value
})

const inputType = computed(() =>
  model.value?._configured && !secretEditing.value ? 'text' : 'password',
)

function onKeyFocus() {
  if (model.value?._configured && !secretEditing.value) {
    secretEditing.value = true
    model.value.api_key = ''
  }
}

function onKeyInput(value) {
  secretEditing.value = true
  model.value.api_key = value
}

watch(
  () => [model.value?._configured, model.value?.api_key_length],
  () => {
    if (!model.value?.api_key) secretEditing.value = false
  },
  { immediate: true },
)

const canTest = computed(() => {
  if (props.hasUrlField && !model.value.url) return false
  return !!(model.value.api_key || model.value._configured)
})
</script>
