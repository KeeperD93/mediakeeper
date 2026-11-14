<template>
  <div class="wz-top">
    <div
      class="wz-prog"
      role="progressbar"
      :aria-label="$t('portal.wizard.progress.label')"
      aria-valuemin="1"
      :aria-valuemax="total"
      :aria-valuenow="num"
      :aria-valuetext="text"
    >
      <span
        v-for="i in total"
        :key="i"
        class="wz-seg"
        :class="{ 'is-done': i < num, 'is-current': i === num }"
      />
    </div>
    <p class="wz-count" aria-live="polite">{{ text }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  num: { type: Number, required: true },
  total: { type: Number, required: true },
})

const { t } = useI18n()
const text = computed(() => t('portal.wizard.progress.text', { n: props.num, total: props.total }))
</script>
