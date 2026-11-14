<template>
  <div class="dd-box wz-map">
    <span class="dd-eyebrow dd-muted">{{ $t('portal.wizard.features.mapTitle') }}</span>

    <!-- From a tablet on: the portal's top bar, drawn small. -->
    <div class="wz-map-desk">
      <div class="wz-nm-box" aria-hidden="true">
        <div class="wz-nm">
          <span class="wz-nm-brand">
            <img :src="LOGO_SRC" alt="" />
            {{ $t('portal.nav.brand') }}
          </span>
          <span class="wz-nm-tab is-on">{{ $t('portal.tabs.home') }}</span>
          <span class="wz-nm-tab">{{ $t('portal.tabs.profile') }}</span>
          <span class="wz-nm-tab">{{ $t('portal.tabs.problems') }}</span>
          <span class="dd-grow" />
          <span class="wz-nm-search">
            <Search :size="15" />
            <span class="wz-nm-ph">{{ $t('portal.search.placeholder') }}</span>
            <span class="wz-nm-go"><ArrowRight :size="15" :stroke-width="2.2" /></span>
          </span>
          <span class="wz-nm-ic"><Library :size="18" :stroke-width="1.8" /></span>
          <span class="wz-nm-ic wz-nm-ic--round"><Calendar :size="18" /></span>
          <span class="wz-nm-ic"><Bell :size="18" /></span>
          <span class="wz-nm-av">
            <WizardAvatar size="md" :initial="wz.initial" :tier="wz.me.tier" />
            <ChevronDown :size="14" :stroke-width="2.2" />
          </span>
        </div>
      </div>
      <ul class="wz-mlegend">
        <li v-for="key in DESK_LEGEND" :key="key">
          {{ $t(`portal.wizard.features.desk.${key}`) }}
        </li>
      </ul>
    </div>

    <!-- On a phone: the top bar, the « + » button and the tabs at the bottom. -->
    <div class="wz-map-phone">
      <div class="wz-mphone" aria-hidden="true">
        <div class="wz-mbar">
          <span class="wz-mbrand">
            <img :src="LOGO_SRC" alt="" />
            {{ $t('portal.nav.brand') }}
          </span>
          <span class="dd-grow" />
          <span class="wz-mic"><Search :size="16" /></span>
          <span class="wz-mic"><Bell :size="16" /></span>
          <WizardAvatar size="md" :initial="wz.initial" :tier="wz.me.tier" />
        </div>
        <span class="wz-mfab"><Plus :size="18" :stroke-width="2.4" /></span>
        <div class="wz-mbottom">
          <span
            v-for="tab in PHONE_TABS"
            :key="tab.label"
            class="wz-mbt"
            :class="{ 'is-on': tab.on }"
          >
            <component :is="tab.icon" :size="18" />
            {{ $t(tab.label) }}
          </span>
        </div>
      </div>
      <ul class="wz-mlegend">
        <li v-for="key in PHONE_LEGEND" :key="key">
          {{ $t(`portal.wizard.features.phone.${key}`) }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import {
  ArrowRight,
  Bell,
  Calendar,
  ChevronDown,
  House,
  Library,
  LifeBuoy,
  Plus,
  Search,
  User,
} from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import WizardAvatar from './WizardAvatar.vue'

const LOGO_SRC = '/assets/icons/mk-logo-128.png'
const DESK_LEGEND = ['tabs', 'search', 'icons', 'avatar', 'fab']
const PHONE_LEGEND = ['tabs', 'top', 'calendar']
// Same tabs as the bottom bar of a member (PortalBottomNav).
const PHONE_TABS = [
  { label: 'portal.tabs.home', icon: House, on: true },
  { label: 'portal.tabs.profile', icon: User },
  { label: 'portal.lists.navLabel', icon: Library },
  { label: 'portal.tabs.problems', icon: LifeBuoy },
]

const wz = inject(ONBOARDING_WIZARD_KEY)
</script>
