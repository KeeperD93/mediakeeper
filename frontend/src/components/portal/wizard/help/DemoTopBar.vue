<template>
  <div class="wzh-pv-nav" :class="{ 'wzh-pv-nav--clear': clear }">
    <span class="wzh-pv-brand">
      <img :src="BRAND_LOGO_SRC" alt="" class="wzh-pv-logo" />
      {{ $t('portal.nav.brand') }}
    </span>
    <span
      v-for="item in TABS"
      :key="item.id"
      class="wzh-pv-tab"
      :class="{ 'is-on': item.id === tab }"
    >
      {{ $t(item.label) }}
    </span>
    <span class="wzh-pv-grow" />
    <span class="wzh-pv-search">
      <span class="wzh-pv-shell" :class="{ 'is-focus': search === DEMO_SEARCH.TYPING }">
        <Search :size="15" />
        <span v-if="search === DEMO_SEARCH.IDLE" class="wzh-pv-ph">
          {{ $t('portal.search.placeholder') }}
        </span>
        <span v-else class="wzh-pv-val">
          <span v-if="search === DEMO_SEARCH.TYPING" class="wzh-typ" :style="typedStyle">
            {{ movie }}
          </span>
          <template v-else>{{ movie }}</template>
          <span v-if="search === DEMO_SEARCH.TYPING" class="wzh-caret" />
        </span>
        <span class="wzh-pv-go" :class="{ 'is-off': search === DEMO_SEARCH.IDLE }">
          <ArrowRight :size="15" :stroke-width="2.2" />
        </span>
      </span>
      <span v-if="search === DEMO_SEARCH.TYPING" class="wzh-pv-pop wzh-pop">
        <span class="wzh-pv-pop-t">{{ $t('portal.search.suggestionsTitle') }}</span>
        <span class="wzh-pv-opt is-on">
          <Search :size="14" />
          {{ movie }}
          <small>· {{ DEMO_DATA.year }}</small>
        </span>
        <span class="wzh-pv-opt">
          <Search :size="14" />
          {{ $t('portal.wizardHelp.screens.sequel') }}
          <small>· {{ DEMO_DATA.sequelYear }}</small>
        </span>
      </span>
    </span>
    <span class="wzh-pv-ic" :class="{ 'is-on': listsOn }">
      <Library :size="18" :stroke-width="1.8" />
    </span>
    <span class="wzh-pv-ic wzh-pv-ic--round"><Calendar :size="18" /></span>
    <span class="wzh-pv-ic"><Bell :size="18" /></span>
    <span class="wzh-pv-avt">
      <WizardAvatar size="md" :initial="initial" :tier="tier" />
      <ChevronDown :size="14" :stroke-width="2.2" />
    </span>
  </div>
</template>

<script setup>
// The portal's top bar, reduced, as a member sees it (no « Demandes » tab): in the help
// demos, and in « where to find » scaled down.
import '@/assets/styles/portal/wizard-help-screens.css'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, Bell, Calendar, ChevronDown, Library, Search } from 'lucide-vue-next'
import { BRAND_LOGO_SRC } from '@/constants/brand'
import { RANK_TIER } from '@/constants/portal'
import { DEMO_DATA, DEMO_SEARCH, DEMO_TAB } from '@/constants/portalWizardHelp'
import WizardAvatar from '../WizardAvatar.vue'

defineProps({
  tab: { type: String, default: DEMO_TAB.NONE },
  clear: { type: Boolean, default: false },
  search: { type: String, default: DEMO_SEARCH.IDLE },
  listsOn: { type: Boolean, default: false },
  initial: { type: String, default: '' },
  // Rank tier of the avatar's ring: the demos show a bronze member.
  tier: { type: String, default: RANK_TIER.BRONZE },
})

const TABS = [
  { id: DEMO_TAB.HOME, label: 'portal.tabs.home' },
  { id: DEMO_TAB.PROFILE, label: 'portal.tabs.profile' },
  { id: DEMO_TAB.PROBLEMS, label: 'portal.tabs.problems' },
]

const { t } = useI18n()
const movie = computed(() => t('portal.wizardHelp.screens.movie'))
// The typing runs one step per letter of the title.
const typedStyle = computed(() => ({ '--wzh-chars': movie.value.length }))
</script>
