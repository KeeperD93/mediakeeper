<template>
  <ol class="wz-path" :aria-label="$t('portal.wizard.expiry.pathLabel')">
    <li>
      <span class="wz-crumb">
        <WizardAvatar :initial="wz.initial" :src="wz.me.avatar_url" :tier="wz.me.tier" />
        {{ $t('portal.wizard.expiry.crumbAvatar') }}
      </span>
    </li>
    <li>
      <ChevronRight class="wz-chev" :size="16" aria-hidden="true" />
      <span class="wz-crumb">{{ $t('portal.avatar.settings') }}</span>
    </li>
    <li>
      <ChevronRight class="wz-chev" :size="16" aria-hidden="true" />
      <span class="wz-crumb is-last">{{ $t('portal.wizard.expiry.crumbAccount') }}</span>
    </li>
  </ol>

  <div class="dd-box wz-set">
    <h2 class="wz-set-title">{{ $t('portal.wizard.expiry.cardTitle') }}</h2>
    <dl>
      <div>
        <dt>{{ $t('portal.wizard.expiry.memberSince') }}</dt>
        <dd>{{ memberSince }}</dd>
      </div>
      <div class="is-hl">
        <dt>{{ $t('portal.wizard.expiry.expiresOn') }}</dt>
        <dd>{{ endsOn || $t('portal.wizard.expiry.noLimit') }}</dd>
      </div>
      <div>
        <dt>{{ $t('portal.wizard.expiry.level') }}</dt>
        <dd>{{ level }}</dd>
      </div>
    </dl>
  </div>

  <div v-if="endsOn">
    <div class="dd-expiry" role="status">
      <span class="dd-expiry-ic"><Clock :size="18" aria-hidden="true" /></span>
      <div class="dd-grow">
        <p class="dd-expiry-t">{{ expiryTitle }}</p>
        <p class="dd-expiry-s">{{ $t('portal.dailyDigest.expiry.hint') }}</p>
      </div>
    </div>
    <p class="wz-cap">{{ $t('portal.wizard.expiry.reminder') }}</p>
  </div>
  <div v-else class="wz-note">
    <Info :size="18" aria-hidden="true" />
    <p>{{ $t('portal.wizard.expiry.none') }}</p>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight, Clock, Info } from 'lucide-vue-next'
import { ONBOARDING_WIZARD_KEY } from '@/composables/portal/useOnboardingWizard'
import { MIN_LEVEL } from '@/constants/portal'
import { localizedDate } from '@/utils/datetime'
import { localizedNumber } from '@/utils/localizedNumber'
import { daysUntil } from '@/utils/portal/onboarding'
import WizardAvatar from './WizardAvatar.vue'

const LONG_DATE = { day: 'numeric', month: 'long', year: 'numeric' }

const { t } = useI18n()
const wz = inject(ONBOARDING_WIZARD_KEY)

const memberSince = computed(() =>
  wz.me.created_at ? localizedDate(wz.me.created_at, LONG_DATE) : '',
)
const endsOn = computed(() =>
  wz.me.access_end_date ? localizedDate(wz.me.access_end_date, LONG_DATE) : '',
)
const level = computed(() =>
  t('portal.wizard.expiry.levelValue', {
    level: wz.me.level || MIN_LEVEL,
    xp: localizedNumber(wz.me.xp || 0),
  }),
)
// The digest's own words: « Your account expires on 12 December 2026, in 29 days. »
const expiryTitle = computed(() => {
  const days = daysUntil(wz.me.access_end_date)
  const when = t('portal.dailyDigest.expiry.when', { n: days }, days)
  return t('portal.dailyDigest.expiry.title', { date: endsOn.value, when })
})
</script>
