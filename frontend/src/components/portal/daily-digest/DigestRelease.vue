<template>
  <section :aria-label="$t('portal.dailyDigest.release.section')">
    <div v-if="!compact" class="dd-sh">
      <h2 class="dd-st">{{ $t('portal.dailyDigest.release.section') }}</h2>
    </div>
    <article
      class="dd-release"
      :class="{
        'dd-release--compact': compact,
        'dd-release--open': open,
        'dd-release--new': view.isNew,
      }"
    >
      <span class="dd-release-icon">
        <Sparkles :size="compact ? 20 : 24" :stroke-width="1.8" aria-hidden="true" />
      </span>
      <div class="dd-grow">
        <div class="dd-release-meta">
          <span v-if="view.isNew" class="dd-new-pill">
            <span class="dd-new-dot" />
            {{ $t('portal.dailyDigest.news.new') }}
          </span>
          <span class="dd-release-tag">v{{ view.version }}</span>
          <span class="dd-release-date">{{ view.date }}</span>
        </div>
        <component :is="compact ? 'h2' : 'h3'" class="dd-release-title">{{ title }}</component>

        <DigestReleaseGroups v-if="open" :groups="view.groups" />
        <p v-else-if="compact" class="dd-release-summary">{{ summary }}</p>
        <ul v-else class="dd-release-teaser">
          <li v-for="(change, i) in view.teaser" :key="i">
            <span class="dd-release-cat" :class="change.toneClass">
              {{ change.labelKey ? $t(change.labelKey) : change.name }}
            </span>
            <span class="dd-release-text">{{ change.text }}</span>
          </li>
        </ul>

        <div class="dd-release-foot">
          <span v-if="moreLabel" class="dd-release-more">{{ moreLabel }}</span>
          <button
            type="button"
            class="dd-release-toggle"
            :aria-expanded="open ? 'true' : 'false'"
            :aria-label="toggleName"
            @click="toggle"
          >
            <span v-if="!open">{{ toggleName }}</span>
            <span class="dd-chev" :class="{ 'dd-chev--up': open }">
              <ChevronDown :size="16" aria-hidden="true" />
            </span>
          </button>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, Sparkles } from 'lucide-vue-next'
import { releaseView } from '@/utils/portal/dailyDigest'
import DigestReleaseGroups from './DigestReleaseGroups.vue'
import '@/assets/styles/portal/daily-digest-release-list.css'
import '@/assets/styles/portal/daily-digest-release.css'

const props = defineProps({
  // The new Portal version of the digest, shown when there is no news to head.
  release: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['open'])

const { t } = useI18n()
const view = computed(() => releaseView(props.release))
const open = ref(false)

const title = computed(() =>
  t(props.compact ? 'portal.dailyDigest.release.titleCompact' : 'portal.dailyDigest.release.title'),
)
const summary = computed(() => view.value.teaser.map(change => change.text).join(' · '))
const moreLabel = computed(() =>
  open.value || props.compact || !view.value.rest
    ? ''
    : t('portal.dailyDigest.release.more', { n: view.value.restLabel }, view.value.rest),
)
const toggleName = computed(() => {
  if (open.value) return t('portal.dailyDigest.release.collapse')
  if (!props.compact) return t('portal.dailyDigest.release.showAll')
  const { total, totalLabel } = view.value
  return t('portal.dailyDigest.release.showAllCompact', { n: totalLabel }, total)
})

// One click anywhere on the card opens every change in place, another one closes it.
function toggle() {
  open.value = !open.value
  if (open.value) emit('open')
}
</script>
