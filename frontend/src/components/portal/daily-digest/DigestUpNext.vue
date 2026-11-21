<template>
  <section :aria-label="$t('portal.dailyDigest.sections.upNext')">
    <div class="ddc-label">{{ $t('portal.dailyDigest.sections.upNext') }}</div>
    <div class="ddc-box">
      <component
        :is="row.to ? 'router-link' : 'div'"
        v-for="row in items"
        :key="row.key"
        :to="row.to"
        class="ddc-row"
        @click="row.to ? $emit('leave') : null"
      >
        <span class="ddc-dot" :class="`dd-tone--${row.tone}`">
          <component :is="row.icon" :size="14" :stroke-width="row.stroke" aria-hidden="true" />
        </span>
        <span class="ddc-row-title">{{ row.text }}</span>
        <span class="ddc-when">{{ row.when }}</span>
      </component>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { FOR_YOU_KIND } from '@/constants/dailyDigest'

const props = defineProps({
  // « For you » rows and events written by useDailyDigestPresenters, in one list.
  rows: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
})
defineEmits(['leave'])

const { t } = useI18n()

const items = computed(() => [
  ...props.rows.map(row => {
    const available = row.kind === FOR_YOU_KIND.REQUEST_AVAILABLE
    return {
      key: row.key,
      to: row.to,
      tone: row.tone,
      icon: row.compactIcon,
      // The check mark reads thin at this size: drawn a little bolder.
      stroke: available ? 2.4 : 2.2,
      text: row.textShort,
      // An available title shows where it leads; the others how long ago they moved.
      when: available && row.to ? t('portal.dailyDigest.forYou.see') : row.ago,
    }
  }),
  ...props.events.map(ev => ({
    key: `event-${ev.id}`,
    to: ev.to,
    tone: 'event',
    icon: ev.icon,
    stroke: 2.2,
    text: ev.title,
    when: ev.when,
  })),
])
</script>
