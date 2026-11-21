<template>
  <div class="dd-box wz-map">
    <span class="dd-eyebrow dd-muted">{{ $t('portal.wizard.features.mapTitle') }}</span>

    <!-- From a tablet on: the portal's top bar of the help demos, scaled down. -->
    <div class="wz-map-desk">
      <div class="wz-nm-box" aria-hidden="true">
        <div class="wz-nm">
          <DemoTopBar :tab="DEMO_TAB.HOME" :initial="wz.initial" :tier="wz.me.tier" />
        </div>
      </div>
      <ul class="wz-mlegend">
        <li v-for="key in DESK_LEGEND" :key="key">
          {{ $t(`portal.wizard.features.desk.${key}`) }}
        </li>
      </ul>
    </div>

    <!-- On a phone: the top bar and the tabs at the bottom; the « + » button is told in
         words, as on a computer. -->
    <div class="wz-map-phone">
      <div class="wz-mphone" aria-hidden="true">
        <div class="wz-mbar">
          <span class="wz-mbrand">
            <img :src="BRAND_LOGO_SRC" alt="" />
            {{ $t('portal.nav.brand') }}
          </span>
          <span class="dd-grow" />
          <span class="wz-mic"><Search :size="16" /></span>
          <span class="wz-mic"><Bell :size="16" /></span>
          <WizardAvatar size="md" :initial="wz.initial" :tier="wz.me.tier" />
        </div>
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
import { Bell, House, Library, LifeBuoy, Search, User } from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import { BRAND_LOGO_SRC } from '@/constants/brand'
import { DEMO_TAB } from '@/constants/portalWizardHelp'
import DemoTopBar from './help/DemoTopBar.vue'
import WizardAvatar from './WizardAvatar.vue'

const DESK_LEGEND = ['tabs', 'search', 'icons', 'avatar', 'fab']
const PHONE_LEGEND = ['tabs', 'top', 'calendar', 'fab']
// Same tabs as the bottom bar of a member (PortalBottomNav).
const PHONE_TABS = [
  { label: 'portal.tabs.home', icon: House, on: true },
  { label: 'portal.tabs.profile', icon: User },
  { label: 'portal.lists.navLabel', icon: Library },
  { label: 'portal.tabs.problems', icon: LifeBuoy },
]

const wz = inject(ONBOARDING_WIZARD_KEY)
</script>
