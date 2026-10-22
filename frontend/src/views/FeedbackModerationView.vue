<template>
  <div class="fbm-page mk-page-root">
    <div class="fbm-tabs" role="tablist" :aria-label="t('feedback.moderation.title')">
      <button
        v-for="tb in TABS"
        :id="`fbm-tab-${tb.status}`"
        :key="tb.status"
        type="button"
        role="tab"
        aria-controls="fbm-panel"
        :aria-selected="tab === tb.status"
        :tabindex="tab === tb.status ? 0 : -1"
        class="fbm-tab"
        :class="{ 'fbm-tab--on': tab === tb.status }"
        @click="switchTab(tb.status)"
      >
        {{ t(tb.labelKey) }}
        <span v-if="tb.counted && tab === tb.status && reports.length" class="fbm-badge">
          {{ reports.length }}
        </span>
      </button>
    </div>

    <div id="fbm-panel" role="tabpanel" :aria-labelledby="`fbm-tab-${tab}`">
      <p v-if="loading" class="fbm-empty">{{ t('common.loading') }}</p>
      <div v-else-if="loadFailed" class="fbm-empty">
        <p class="fbm-error">{{ t('feedback.moderation.loadError') }}</p>
        <button type="button" class="fbm-btn" @click="load">
          {{ t('feedback.moderation.retry') }}
        </button>
      </div>
      <p v-else-if="!reports.length" class="fbm-empty">
        {{ emptyLabel }}
      </p>

      <ul v-else class="fbm-list">
        <FeedbackReportCard
          v-for="r in reports"
          :key="r.id"
          :report="r"
          :editing="editingId === r.id"
          :actions="tab === FEEDBACK_STATUS.PENDING"
          :busy="isBusy(r.id)"
          @edit="startEdit(r)"
          @validate="validate(r)"
          @reject="reject(r)"
        >
          <FeedbackReportForm
            v-model="form"
            :busy="isBusy(r.id)"
            :can-save="canSave"
            @toggle-platform="togglePlatform"
            @toggle-tag="toggleTag"
            @save="save"
            @cancel="cancelEdit"
          />
        </FeedbackReportCard>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import FeedbackReportCard from '@/components/feedback/FeedbackReportCard.vue'
import FeedbackReportForm from '@/components/feedback/FeedbackReportForm.vue'
import { useFeedbackModeration } from '@/composables/useFeedbackModeration'
import { FEEDBACK_STATUS } from '@/constants/feedback'
import '@/assets/styles/feedback-moderation.css'

// The queue tabs; only the pending one counts its reports.
const TABS = [
  {
    status: FEEDBACK_STATUS.PENDING,
    labelKey: 'feedback.moderation.tabPending',
    emptyKey: 'feedback.moderation.empty',
    counted: true,
  },
  {
    status: FEEDBACK_STATUS.REJECTED,
    labelKey: 'feedback.moderation.tabRejected',
    emptyKey: 'feedback.moderation.emptyRejected',
    counted: false,
  },
]

const { t } = useI18n()
const {
  tab,
  reports,
  loading,
  loadFailed,
  editingId,
  form,
  canSave,
  isBusy,
  load,
  switchTab,
  startEdit,
  cancelEdit,
  togglePlatform,
  toggleTag,
  save,
  validate,
  reject,
} = useFeedbackModeration()

const emptyLabel = computed(() => t(TABS.find(tb => tb.status === tab.value).emptyKey))

onMounted(load)
</script>
