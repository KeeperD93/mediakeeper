<template>
  <div :class="look.item">
    <button
      type="button"
      :class="look.row"
      :aria-expanded="open ? 'true' : 'false'"
      @click="$emit('toggle')"
    >
      <span class="dd-badge" :class="look.badgeTone">{{ badge }}</span>
      <span :class="look.title">{{ title }}</span>
      <span :class="look.when">{{ until }}</span>
      <span v-if="!compact" class="dd-chev" :class="{ 'dd-chev--up': open }">
        <ChevronDown :size="16" aria-hidden="true" />
      </span>
    </button>
    <div v-if="open" :class="look.body">
      <p v-for="(text, i) in boost.paragraphs" :key="i">{{ text }}</p>
      <p v-if="actions">{{ actions }}</p>
      <p class="dd-boost-end">{{ ends }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown } from 'lucide-vue-next'
import '@/assets/styles/portal/daily-digest-news.css'
import '@/assets/styles/portal/daily-digest-compact-news.css'
import '@/assets/styles/portal/daily-digest-boost.css'

const props = defineProps({
  // A running XP boost, as boostView draws it.
  boost: { type: Object, required: true },
  open: { type: Boolean, default: false },
  // A line of the compact view's list box, without the chevron.
  compact: { type: Boolean, default: false },
})
defineEmits(['toggle'])

const { t, locale } = useI18n()
const k = key => `portal.dailyDigest.boost.${key}`

// The row and body of the other rows of each view, tinted green, or orange under ×1.
const look = computed(() => {
  const { reduced } = props.boost
  const tone = reduced ? 'dd-boost--down' : 'dd-boost--up'
  const badgeTone = reduced ? 'dd-badge--warn' : 'dd-badge--boost'
  if (props.compact) {
    return {
      item: ['dd-boost-row', tone],
      row: 'ddc-row ddc-row-item',
      badgeTone,
      title: 'ddc-row-title',
      when: 'ddc-when',
      body: 'ddc-rowbody',
    }
  }
  return {
    item: ['dd-more-item', 'dd-more-item--boost', tone, { 'dd-more-item--open': props.open }],
    row: 'dd-more-row',
    badgeTone,
    title: 'dd-more-title',
    when: 'dd-more-date',
    body: 'dd-more-body',
  }
})

const badge = computed(() => t(k(props.boost.reduced ? 'badgeReduced' : 'badge')))
const title = computed(() =>
  t(k('line'), { name: props.boost.name, multiplier: props.boost.multiplier }),
)
const until = computed(() => t(k('until'), { date: props.boost.until }))
// An action the portal has no name for keeps its own.
const actions = computed(() => {
  const names = props.boost.actions.map(({ key, action }) => t(key, action))
  if (!names.length) return ''
  return t(k('counts'), { actions: new Intl.ListFormat(locale.value).format(names) })
})
const ends = computed(() => {
  const { ends: date, leftKey, left, leftLabel } = props.boost
  return t(k('ends'), { date, left: t(leftKey, { n: leftLabel }, left) })
})
</script>
