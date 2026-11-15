<template>
  <!-- 1. Home page: the featured title is requested from its banner. -->
  <div class="wzh-frame" :class="shown(0)">
    <div class="wzh-pv-art" />
    <DemoTopBar clear :tab="DEMO_TAB.HOME" :initial="initial" />
    <div class="wzh-pv-hero">
      <p class="wzh-pv-hero-t">{{ movie }}</p>
      <p class="wzh-pv-rank">
        <Flame :size="15" />
        {{ $t('portal.hero.topRank', { rank: DEMO_DATA.trendingRank }) }}
      </p>
      <p class="wzh-pv-ov">{{ $t('portal.wizardHelp.screens.overview') }}</p>
      <div class="wzh-pv-acts">
        <span class="wzh-pv-hbtn wzh-pv-hbtn--play">
          <Plus :size="20" :stroke-width="2.5" />
          {{ $t('portal.card.requestBtn') }}
        </span>
        <span class="wzh-pv-hbtn">
          <Video :size="20" />
          {{ $t('portal.detail.watchTrailer') }}
        </span>
        <span class="wzh-pv-hbtn wzh-pv-hbtn--icon"><Info :size="20" /></span>
      </div>
    </div>
    <div class="wzh-pv-dots">
      <i v-for="n in DEMO_DATA.heroSlides" :key="n" :class="{ 'is-on': n === 1 }" />
    </div>
  </div>

  <!-- 2. Search: the title is typed in the top bar, a suggestion is picked. -->
  <div class="wzh-frame" :class="shown(1)">
    <DemoTopBar :tab="DEMO_TAB.HOME" :search="DEMO_SEARCH.TYPING" :initial="initial" />
    <div class="wzh-pv-page">
      <p class="wzh-pv-rowt">{{ $t('portal.sections.trending') }}</p>
      <div class="wzh-pv-posters">
        <span v-for="poster in TRENDING" :key="poster.key" class="wzh-pv-poster">
          <span class="wzh-pv-pa" :class="`wzh-pv-tint-${poster.tint}`">
            {{ $t(`portal.wizardHelp.screens.${poster.key}`) }}
          </span>
        </span>
      </div>
    </div>
  </div>

  <!-- 3. Results: the title's poster opens its page. -->
  <div class="wzh-frame" :class="shown(2)">
    <DemoTopBar :search="DEMO_SEARCH.FILLED" :initial="initial" />
    <div class="wzh-pv-page">
      <p class="wzh-pv-h1">{{ $t('portal.search.resultsTitle', { query: movie }) }}</p>
      <p class="wzh-pv-sub">{{ $t('portal.search.resultsSubtitle') }}</p>
      <div class="wzh-pv-posters">
        <span class="wzh-pv-poster">
          <span class="wzh-pv-pa wzh-pv-tint-blue">
            <span class="wzh-pv-panel">
              <span class="wzh-pv-panel-t">{{ movie }}</span>
              <span class="wzh-pv-panel-m">
                <span>{{ DEMO_DATA.year }} · {{ $t('portal.wizardHelp.screens.runtime') }}</span>
                <span class="wzh-pv-star">
                  <Star :size="11" />
                  {{ DEMO_DATA.rating }}%
                </span>
              </span>
              <span class="wzh-pv-panel-a">
                <span class="wzh-pv-mkbtn">
                  <Plus :size="13" />
                  {{ $t('portal.card.requestBtn') }}
                </span>
                <span class="wzh-pv-mkic"><Bookmark :size="13" /></span>
              </span>
            </span>
          </span>
          <MousePointer2 class="wzh-cur" :size="22" />
        </span>
        <span v-for="poster in RESULTS" :key="poster.key" class="wzh-pv-poster">
          <span class="wzh-pv-pa" :class="`wzh-pv-tint-${poster.tint}`">
            {{ $t(`portal.wizardHelp.screens.${poster.key}`) }}
          </span>
        </span>
      </div>
    </div>
  </div>

  <!-- 4. The title's page: « Demander ». -->
  <div class="wzh-frame" :class="shown(3)">
    <DemoTopBar :search="DEMO_SEARCH.FILLED" :initial="initial" />
    <DemoTitleSheet :press="DEMO_PRESS.REQUEST" />
  </div>

  <!-- 5. The request window: « Valider la demande ». -->
  <div class="wzh-frame" :class="shown(4)">
    <DemoTopBar :search="DEMO_SEARCH.FILLED" :initial="initial" />
    <DemoTitleSheet />
    <div class="wzh-pv-ovl">
      <div class="wzh-pv-dialog wzh-pv-dialog--request">
        <p class="wzh-pv-mh">
          {{ $t('portal.request.title') }}
          <X :size="14" />
        </p>
        <div class="wzh-pv-rm-m">
          <span class="wzh-pv-thumb wzh-pv-tint-blue" />
          <span>
            <b>{{ movie }}</b>
            <span>{{ DEMO_DATA.year }} · {{ $t('portal.card.movie') }}</span>
          </span>
        </div>
        <div class="wzh-pv-mf">
          <span class="wzh-pv-rm-btn wzh-prs">
            {{ $t('portal.request.submit') }}
            <MousePointer2 class="wzh-cur" :size="22" />
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- 6. Sent: the title is « Demandé », the toast counts the month's quota. -->
  <div class="wzh-frame" :class="shown(5)">
    <DemoTopBar :search="DEMO_SEARCH.FILLED" :initial="initial" />
    <DemoTitleSheet requested />
    <div class="wzh-pv-toast wzh-tst">
      <span class="wzh-pv-toast-ic"><Check :size="16" :stroke-width="2.4" /></span>
      <span class="wzh-pv-toast-bar" />
      <p>
        {{ $t('portal.request.quotaInfo', { used: DEMO_DATA.quotaUsed, max: DEMO_DATA.quotaMax }) }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bookmark, Check, Flame, Info, MousePointer2, Plus, Star, Video, X } from 'lucide-vue-next'
import DemoTitleSheet from './DemoTitleSheet.vue'
import DemoTopBar from './DemoTopBar.vue'
import { DEMO_DATA, DEMO_PRESS, DEMO_SEARCH, DEMO_TAB } from '@/constants/portalWizardHelp'

const props = defineProps({
  frame: { type: Number, default: 0 },
  initial: { type: String, default: '' },
})

const TRENDING = [
  { key: 'movie', tint: 'blue' },
  { key: 'lighthouse', tint: 'teal' },
  { key: 'gardens', tint: 'pink' },
  { key: 'lisbon', tint: 'orange' },
  { key: 'orbit', tint: 'violet' },
]
const RESULTS = [
  { key: 'sequel', tint: 'slate' },
  { key: 'extras', tint: 'amber' },
]

const { t } = useI18n()
const movie = computed(() => t('portal.wizardHelp.screens.movie'))
const shown = index => ({ 'is-shown': props.frame === index })
</script>
