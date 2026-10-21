<template>
  <li class="fbm-card">
    <div class="fbm-head">
      <span class="fbm-type" :class="`fbm-type--${report.type}`">
        {{ t(`feedback.modal.type_${report.type}`) }}
      </span>
      <h2 class="fbm-title">{{ report.title }}</h2>
      <time class="fbm-date" :datetime="report.created_at">
        {{ formatDate(report.created_at) }}
      </time>
    </div>

    <p class="fbm-meta">{{ metaLine }}</p>
    <p v-if="location" class="fbm-loc">{{ location }}</p>

    <slot v-if="editing" />
    <template v-else>
      <p class="fbm-desc">{{ report.description }}</p>
      <p v-if="report.reproduction" class="fbm-repro">
        <strong>{{ t('feedback.moderation.reproduction') }}</strong>
        {{ report.reproduction }}
      </p>
      <ul v-if="report.tags?.length" class="fbm-taglist">
        <li v-for="tag in report.tags" :key="tag" class="fbm-tag">{{ tagLabel(tag) }}</li>
      </ul>

      <div v-if="actions" class="fbm-actions">
        <button type="button" class="fbm-btn" :disabled="busy" @click="emit('edit')">
          {{ t('feedback.moderation.edit') }}
        </button>
        <button
          type="button"
          class="fbm-btn fbm-btn--go"
          :disabled="busy"
          @click="emit('validate')"
        >
          {{ t('feedback.moderation.validate') }}
        </button>
        <button type="button" class="fbm-btn fbm-btn--no" :disabled="busy" @click="emit('reject')">
          {{ t('feedback.moderation.reject') }}
        </button>
      </div>
    </template>
  </li>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { localizedDateTime } from '@/utils/datetime'
import { FEEDBACK_PLATFORM_BOTH } from '@/constants/feedback'
import '@/assets/styles/feedback-moderation.css'

const props = defineProps({
  report: { type: Object, required: true },
  // The default slot (the edit form) then takes the place of the read view.
  editing: { type: Boolean, default: false },
  // Edit / validate / reject buttons: pending reports only.
  actions: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['edit', 'validate', 'reject'])
const { t } = useI18n()

const location = computed(() =>
  [props.report.zone, props.report.module, props.report.tab].filter(Boolean).join(' · '),
)

const metaLine = computed(() => {
  const r = props.report
  const parts = [
    r.anonymous || !r.reporter_name
      ? t('feedback.moderation.anonymous')
      : t('feedback.moderation.by', { name: r.reporter_name }),
  ]
  if (r.platform) parts.push(platformLabel(r.platform))
  if (r.resolution) parts.push(r.resolution)
  return parts.join(' · ')
})

function platformLabel(p) {
  if (p === FEEDBACK_PLATFORM_BOTH) return t('feedback.moderation.platformBoth')
  return t(`feedback.modal.platform_${p}`)
}

function tagLabel(tag) {
  const key = `feedback.tags.${tag}`
  const label = t(key)
  return label === key ? tag : label
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return localizedDateTime(d, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>
