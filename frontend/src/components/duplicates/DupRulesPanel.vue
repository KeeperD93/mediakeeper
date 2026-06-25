<template>
  <p class="rules-desc">{{ $t('duplicates.rulesDescription') }}</p>
  <div class="rules-list">
    <div v-for="(rule, ri) in rules" :key="ri" class="rule-row">
      <select v-model="rule.field" class="rule-sel mk-select-chevron">
        <option value="resolution">{{ $t('duplicates.ruleResolution') }}</option>
        <option value="codec">{{ $t('duplicates.ruleCodec') }}</option>
        <option value="keep_largest">{{ $t('duplicates.ruleKeepLargest') }}</option>
        <option value="keep_smallest">{{ $t('duplicates.ruleKeepSmallest') }}</option>
      </select>
      <input
        v-if="rule.field === 'resolution'"
        v-model="rule.value"
        class="rule-input"
        placeholder="ex: 1080p"
      />
      <input
        v-else-if="rule.field === 'codec'"
        v-model="rule.value"
        class="rule-input"
        placeholder="ex: HEVC"
      />
      <span v-else class="rule-auto">{{ $t('duplicates.automatic') }}</span>
      <button class="rule-del" @click="removeRule(ri)">✕</button>
    </div>
  </div>
  <button class="doub-btn doub-btn-secondary doub-btn-spaced" @click="addRule">
    {{ $t('duplicates.addRule') }}
  </button>
</template>

<script setup>
const rules = defineModel({ type: Array, default: () => [] })
const emit = defineEmits(['save'])

function removeRule(i) {
  rules.value.splice(i, 1)
  emit('save')
}
function addRule() {
  rules.value.push({ field: 'keep_largest', value: '' })
  emit('save')
}
</script>
