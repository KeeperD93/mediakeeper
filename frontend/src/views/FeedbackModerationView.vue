<template>
  <div class="fbm-page mk-page-root">
    <div class="fbm-tabs" role="tablist" :aria-label="t('feedback.moderation.title')">
      <button
        id="fbm-tab-pending"
        type="button"
        role="tab"
        aria-controls="fbm-panel"
        :aria-selected="tab === 'pending'"
        :tabindex="tab === 'pending' ? 0 : -1"
        class="fbm-tab"
        :class="{ 'fbm-tab--on': tab === 'pending' }"
        @click="switchTab('pending')"
      >
        {{ t('feedback.moderation.tabPending') }}
        <span v-if="tab === 'pending' && reports.length" class="fbm-badge">
          {{ reports.length }}
        </span>
      </button>
      <button
        id="fbm-tab-rejected"
        type="button"
        role="tab"
        aria-controls="fbm-panel"
        :aria-selected="tab === 'rejected'"
        :tabindex="tab === 'rejected' ? 0 : -1"
        class="fbm-tab"
        :class="{ 'fbm-tab--on': tab === 'rejected' }"
        @click="switchTab('rejected')"
      >
        {{ t('feedback.moderation.tabRejected') }}
      </button>
    </div>

    <div id="fbm-panel" role="tabpanel" :aria-labelledby="`fbm-tab-${tab}`">
      <p v-if="loading" class="fbm-empty">{{ t('common.loading') }}</p>
      <p v-else-if="!reports.length" class="fbm-empty">
        {{ emptyLabel }}
      </p>

      <ul v-else class="fbm-list">
        <FeedbackReportCard
          v-for="r in reports"
          :key="r.id"
          :report="r"
          :editing="editingId === r.id"
          :actions="tab === 'pending'"
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
import '@/assets/styles/feedback-moderation.css'

const { t } = useI18n()
const {
  tab,
  reports,
  loading,
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

const emptyLabel = computed(() =>
  t(tab.value === 'pending' ? 'feedback.moderation.empty' : 'feedback.moderation.emptyRejected'),
)

onMounted(load)
</script>
