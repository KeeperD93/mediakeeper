<template>
  <div class="wz-feats">
    <div v-for="item in FEATURES" :key="item.key" class="wz-feat">
      <span class="wz-ic" :class="`wz-tone--${item.tone}`">
        <component :is="item.icon" :size="20" aria-hidden="true" />
      </span>
      <div class="dd-grow">
        <h2 class="wz-ft">{{ $t(`portal.wizard.features.items.${item.key}.title`) }}</h2>
        <p class="wz-fd">{{ $t(`portal.wizard.features.items.${item.key}.text`) }}</p>
        <span class="dd-badge dd-badge--pin wz-fw">
          {{ $t(`portal.wizard.features.items.${item.key}.where`) }}
        </span>
      </div>
    </div>
  </div>
  <WizardNavMap />
</template>

<script setup>
import { Bell, Calendar, CirclePlus, Crown, Library, LifeBuoy, Search, User } from 'lucide-vue-next'
import WizardNavMap from './WizardNavMap.vue'

// What a member can do, and where it is (no « Requests » tab: it is the admins').
const FEATURES = [
  { key: 'request', icon: Search, tone: 'accent' },
  { key: 'profile', icon: User, tone: 'purple' },
  { key: 'ranking', icon: Crown, tone: 'gold' },
  { key: 'lists', icon: Library, tone: 'cyan' },
  { key: 'issues', icon: LifeBuoy, tone: 'blue' },
  { key: 'calendar', icon: Calendar, tone: 'pink' },
  { key: 'fab', icon: CirclePlus, tone: 'green' },
  { key: 'notifications', icon: Bell, tone: 'rose' },
]
</script>
