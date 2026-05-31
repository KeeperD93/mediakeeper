<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.anomalyDesc') }}</p>
    <div class="mm-rule-stack">
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkResolution" type="checkbox" class="mm-chkbox" />
        <div>
          <div class="mm-rule-label">{{ $t('mediaManager.ruleResolution') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleResolutionHint') }}</div>
        </div>
      </label>
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkYear" type="checkbox" class="mm-chkbox" />
        <div>
          <div class="mm-rule-label">{{ $t('mediaManager.ruleYear') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleYearHint') }}</div>
        </div>
      </label>
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkDoubleSpaces" type="checkbox" class="mm-chkbox" />
        <div>
          <div class="mm-rule-label">{{ $t('mediaManager.ruleDoubleSpaces') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleDoubleSpacesHint') }}</div>
        </div>
      </label>
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkMultipleUnderscores" type="checkbox" class="mm-chkbox" />
        <div>
          <div class="mm-rule-label">{{ $t('mediaManager.ruleUnderscores') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleUnderscoresHint') }}</div>
        </div>
      </label>
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkDotsCount" type="checkbox" class="mm-chkbox" />
        <div class="mm-rule-text">
          <div class="mm-rule-label">{{ $t('mediaManager.ruleDots') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleDotsHint') }}</div>
        </div>
        <div class="mm-rule-max">
          <span class="mm-rule-max-label">{{ $t('mediaManager.ruleMax') }}</span>
          <input
            v-model.number="anomalyDraft.maxDots"
            type="number"
            min="1"
            max="20"
            class="mm-rule-num"
            :disabled="!anomalyDraft.checkDotsCount"
          />
        </div>
      </label>
      <label class="mm-rule-row">
        <input v-model="anomalyDraft.checkNameLength" type="checkbox" class="mm-chkbox" />
        <div class="mm-rule-text">
          <div class="mm-rule-label">{{ $t('mediaManager.ruleLength') }}</div>
          <div class="mm-rule-hint">{{ $t('mediaManager.ruleLengthHint') }}</div>
        </div>
        <div class="mm-rule-max">
          <span class="mm-rule-max-label">{{ $t('mediaManager.ruleMax') }}</span>
          <input
            v-model.number="anomalyDraft.maxNameLength"
            type="number"
            min="50"
            max="500"
            class="mm-rule-num"
            :disabled="!anomalyDraft.checkNameLength"
          />
        </div>
      </label>
    </div>
    <div class="mm-config-footer">
      <button
        class="mm-btn-sm mm-btn-success"
        :class="{ 'mm-btn-saved': saved }"
        @click="$emit('save')"
      >
        <Check />
        {{ saved ? $t('common.saved') + ' ✓' : $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'

const anomalyDraft = defineModel('anomalyDraft', { type: Object, required: true })
defineProps({
  saved: { type: Boolean, default: false },
})
defineEmits(['save'])
</script>

<style scoped>
.mm-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.mm-rule-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.mm-rule-text {
  flex: 1;
}
.mm-rule-max {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
}
.mm-rule-max-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
</style>
