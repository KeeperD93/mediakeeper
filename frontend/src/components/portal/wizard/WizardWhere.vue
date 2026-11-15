<template>
  <p class="wz-where">
    {{ lead ? `${lead} ` : '' }}
    <i18n-t :keypath="`portal.wizard.where.${when}`" tag="span">
      <template #path>
        <b>{{ $t(`portal.wizard.paths.${path}`) }}</b>
      </template>
    </i18n-t>
  </p>
</template>

<script setup>
// « To change later: Settings › Preferences », the path in bold, after an optional lead.
import { I18nT } from 'vue-i18n'

defineProps({
  when: {
    type: String,
    default: 'later',
    validator: value => ['later', 'anytime'].includes(value),
  },
  path: { type: String, required: true },
  lead: { type: String, default: '' },
})
</script>
