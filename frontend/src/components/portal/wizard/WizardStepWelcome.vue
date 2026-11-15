<template>
  <div class="dd-box wz-plan">
    <ol :aria-label="$t('portal.wizard.welcome.planLabel')">
      <li v-for="item in PLAN" :key="item.key" :class="{ 'is-opt': item.optional }">
        {{ $t(`portal.wizard.welcome.plan.${item.key}`) }}
      </li>
    </ol>
  </div>
  <p class="wz-time">{{ $t('portal.wizard.welcome.note') }}</p>
</template>

<script setup>
import { WIZARD_STEP as S } from '@/constants/portalOnboarding'

// The counted steps, the optional ones marked.
const PLAN = [
  { key: S.NAME },
  { key: S.LANGUAGE },
  { key: S.VISIBILITY },
  { key: S.FEATURES },
  { key: S.HELP },
  { key: S.EXPIRY },
  { key: S.NOTIFICATIONS, optional: true },
  { key: S.GENRES, optional: true },
  { key: S.AVATAR, optional: true },
]
</script>
