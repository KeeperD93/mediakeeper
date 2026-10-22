<template>
  <form class="fbm-edit" @submit.prevent="emit('save')">
    <div class="fbm-types">
      <button
        v-for="ty in FEEDBACK_TYPES"
        :key="ty"
        type="button"
        class="fbm-chip"
        :class="{ 'fbm-chip--on': form.type === ty }"
        :aria-pressed="form.type === ty"
        @click="form.type = ty"
      >
        {{ t(`feedback.modal.type_${ty}`) }}
      </button>
    </div>

    <label class="fbm-field">
      <span>{{ t('feedback.modal.titleField') }}</span>
      <input v-model="form.title" type="text" :maxlength="FEEDBACK_MAX.title" class="fbm-input" />
    </label>

    <label class="fbm-field">
      <span>{{ t('feedback.modal.descField') }}</span>
      <textarea
        v-model="form.description"
        :maxlength="FEEDBACK_MAX.description"
        rows="4"
        class="fbm-input"
      />
    </label>

    <label class="fbm-field">
      <span>{{ t('feedback.modal.reproField') }}</span>
      <textarea
        v-model="form.reproduction"
        :maxlength="FEEDBACK_MAX.reproduction"
        rows="2"
        class="fbm-input"
      />
    </label>

    <label class="fbm-field">
      <span>{{ t('feedback.modal.resolution') }}</span>
      <input
        v-model="form.resolution"
        type="text"
        :maxlength="FEEDBACK_MAX.resolution"
        class="fbm-input"
        :placeholder="t('feedback.modal.resolutionPlaceholder')"
      />
    </label>

    <fieldset class="fbm-field">
      <legend>{{ t('feedback.modal.platform') }}</legend>
      <div class="fbm-chips">
        <button
          v-for="p in FEEDBACK_PLATFORMS"
          :key="p"
          type="button"
          class="fbm-chip"
          :class="{ 'fbm-chip--on': form.platforms.includes(p) }"
          :aria-pressed="form.platforms.includes(p)"
          @click="emit('toggle-platform', p)"
        >
          {{ t(`feedback.modal.platform_${p}`) }}
        </button>
      </div>
    </fieldset>

    <fieldset class="fbm-field">
      <legend>{{ t('feedback.modal.tags') }}</legend>
      <div class="fbm-chips">
        <button
          v-for="tag in FEEDBACK_TAGS"
          :key="tag"
          type="button"
          class="fbm-chip"
          :class="{ 'fbm-chip--on': form.tags.includes(tag) }"
          :aria-pressed="form.tags.includes(tag)"
          @click="emit('toggle-tag', tag)"
        >
          {{ t(`feedback.tags.${tag}`) }}
        </button>
      </div>
    </fieldset>

    <div class="fbm-actions">
      <button type="button" class="fbm-btn" :disabled="busy" @click="emit('cancel')">
        {{ t('feedback.moderation.cancel') }}
      </button>
      <button type="submit" class="fbm-btn fbm-btn--go" :disabled="!canSave || busy">
        {{ t('feedback.moderation.save') }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import {
  FEEDBACK_TYPES,
  FEEDBACK_PLATFORMS,
  FEEDBACK_TAGS,
  FEEDBACK_MAX,
} from '@/constants/feedback'
import '@/assets/styles/feedback-moderation.css'

// The draft of the report being edited: its fields change in place.
const form = defineModel({ type: Object, required: true })
defineProps({
  busy: { type: Boolean, default: false },
  canSave: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle-platform', 'toggle-tag', 'save', 'cancel'])
const { t } = useI18n()
</script>
