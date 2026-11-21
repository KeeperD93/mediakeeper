<template>
  <div class="dd-prog-left">
    <div class="dd-lvl">
      <div
        class="dd-ring"
        role="img"
        :aria-label="level.ringLabel"
        :style="{ '--dd-ring-pct': `${level.percent}%` }"
      >
        <div class="dd-ring-in">
          <b>{{ level.level }}</b>
          <small>{{ $t('portal.dailyDigest.level.ringUnit') }}</small>
        </div>
      </div>
      <div class="dd-grow">
        <span class="dd-eyebrow dd-eyebrow--level">
          {{ $t('portal.dailyDigest.level.eyebrow') }}
        </span>
        <h3 class="dd-ttl">
          <span class="dd-ttl-text">{{ level.title }}</span>
          <span v-if="level.xpYesterday" class="dd-xpchip">{{ level.xpYesterday }}</span>
        </h3>
        <div class="dd-bar">
          <span class="dd-bar-fill dd-bar-fill--level" :style="{ width: `${level.percent}%` }" />
        </div>
        <div class="dd-meta">
          <span>{{ level.progress }}</span>
          <span class="dd-meta-level">{{ level.toNext }}</span>
        </div>
      </div>
    </div>

    <div v-if="achievement" class="dd-ach">
      <div class="dd-ach-ic"><Trophy :size="28" aria-hidden="true" /></div>
      <div class="dd-grow">
        <span class="dd-eyebrow dd-eyebrow--ach">
          {{ $t('portal.dailyDigest.sections.nextAchievement') }}
        </span>
        <h3 class="dd-ttl">
          <span class="dd-ttl-text">{{ achievement.name }}</span>
        </h3>
        <p v-if="achievement.description" class="dd-desc">{{ achievement.description }}</p>
        <div class="dd-bar">
          <span
            class="dd-bar-fill dd-bar-fill--ach"
            :style="{ width: `${achievement.percent}%` }"
          />
        </div>
        <div class="dd-meta">
          <span>{{ achievement.count }}</span>
          <span class="dd-meta-ach">{{ achievement.remaining }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Trophy } from 'lucide-vue-next'

defineProps({
  // Written by useDailyDigestPresenters (`level`, `achievement`).
  level: { type: Object, required: true },
  achievement: { type: Object, default: null },
})
</script>
