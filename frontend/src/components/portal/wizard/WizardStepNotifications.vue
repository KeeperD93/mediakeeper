<template>
  <div class="dd-box wz-uses">
    <span class="dd-eyebrow dd-muted">{{ $t('portal.wizard.notifications.usesTitle') }}</span>
    <ul>
      <li v-for="use in USES" :key="use.key">
        <span class="wz-ic wz-ic--sm" :class="`wz-tone--${use.tone}`">
          <component :is="use.icon" :size="16" aria-hidden="true" />
        </span>
        {{ $t(`portal.wizard.notifications.uses.${use.key}`) }}
      </li>
    </ul>
  </div>

  <div v-if="state === NOTIFY_STATE.GRANTED" class="wz-note wz-note--ok" role="status">
    <BellRing :size="18" aria-hidden="true" />
    <p>{{ $t('portal.wizard.notifications.enabled') }}</p>
  </div>
  <div v-else-if="unavailable" class="wz-note">
    <Info :size="18" aria-hidden="true" />
    <p>{{ $t(`portal.wizard.notifications.${state}`) }}</p>
  </div>
  <template v-else>
    <button
      v-if="state === NOTIFY_STATE.DEFAULT"
      type="button"
      class="wz-ghost wz-ask"
      @click="ask"
    >
      <Bell :size="16" aria-hidden="true" />
      {{ $t('portal.wizard.notifications.enable') }}
    </button>
    <p v-else class="wz-where">{{ $t('portal.wizard.notifications.denied') }}</p>

    <div v-if="wz.notify.confirm" class="wz-note wz-note--warn wz-confirm" role="alert">
      <BellOff :size="18" aria-hidden="true" />
      <div>
        <p ref="confirmTitleRef" class="wz-confirm-t" tabindex="-1">
          {{ $t('portal.wizard.notifications.confirmTitle') }}
        </p>
        <p>{{ $t('portal.wizard.notifications.confirmText') }}</p>
        <div class="wz-confirm-actions">
          <button v-if="state === NOTIFY_STATE.DEFAULT" type="button" class="wz-ghost" @click="ask">
            {{ $t('portal.wizard.notifications.retry') }}
          </button>
          <button type="button" class="wz-ghost" @click="wz.leaveNotifications()">
            {{ $t('portal.wizard.notifications.continueWithout') }}
          </button>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup>
import { computed, inject, nextTick, ref, watch } from 'vue'
import {
  Bell,
  BellOff,
  BellRing,
  CalendarHeart,
  Info,
  LifeBuoy,
  Newspaper,
  Sparkles,
} from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import { NOTIFY_STATE } from '@/constants/portalOnboarding'

// What the portal will tell, once the person allows it on this device.
const USES = [
  { key: 'requests', icon: Sparkles, tone: 'green' },
  { key: 'issues', icon: LifeBuoy, tone: 'blue' },
  { key: 'invitations', icon: CalendarHeart, tone: 'pink' },
  { key: 'news', icon: Newspaper, tone: 'accent' },
]

const wz = inject(ONBOARDING_WIZARD_KEY)
const confirmTitleRef = ref(null)
const state = computed(() => wz.notify.state)
const unavailable = computed(() =>
  [NOTIFY_STATE.INSECURE, NOTIFY_STATE.UNSUPPORTED].includes(state.value),
)

const ask = () => wz.notify.ask()

// « Are you sure? » takes the focus, so it is read before anything else.
watch(
  () => wz.notify.confirm,
  shown => {
    if (shown) nextTick(() => confirmTitleRef.value?.focus())
  },
)
</script>
