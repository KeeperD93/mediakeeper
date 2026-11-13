<template>
  <div class="dd-full">
    <DigestHero :me="digest.me" :date="formattedDate" :greeting="greeting" />

    <DigestExpiry v-if="expiry" :expiry="expiry" />

    <DigestNews
      v-if="digest.news?.length"
      :news="digest.news"
      :release="digest.release"
      @read="$emit('read-news', $event)"
      @seen="$emit('seen-news', $event)"
      @open-release="$emit('open-release')"
    />
    <DigestRelease
      v-else-if="digest.release"
      :release="digest.release"
      @open="$emit('open-release')"
    />

    <DigestStats v-if="statCards.length" :cards="statCards" />

    <section v-if="level" :aria-label="$t('portal.dailyDigest.sections.progress')">
      <div class="dd-sh">
        <h2 class="dd-st">{{ $t('portal.dailyDigest.sections.progress') }}</h2>
      </div>
      <div class="dd-prog">
        <DigestProgress :level="level" :achievement="achievement" />
        <DigestPodium
          v-if="podiumEntries.length"
          :entries="podiumEntries"
          @leave="$emit('leave')"
        />
      </div>
    </section>

    <DigestPosters
      v-if="digest.recent_adds?.length"
      :items="digest.recent_adds"
      @leave="$emit('leave')"
    />

    <DigestForYou v-if="forYou.length" :rows="forYou" @leave="$emit('leave')" />

    <DigestEvents v-if="events.length" :events="events" @leave="$emit('leave')" />

    <footer class="dd-foot">
      <p class="dd-foot-text">{{ $t('portal.dailyDigest.footer') }}</p>
      <button type="button" class="dd-cta" @click="$emit('close')">
        {{ $t('common.close') }}
      </button>
    </footer>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { useDailyDigestPresenters } from '@/composables/portal/useDailyDigestPresenters'
import DigestEvents from './DigestEvents.vue'
import DigestExpiry from './DigestExpiry.vue'
import DigestForYou from './DigestForYou.vue'
import DigestHero from './DigestHero.vue'
import DigestNews from './DigestNews.vue'
import DigestPodium from './DigestPodium.vue'
import DigestPosters from './DigestPosters.vue'
import DigestProgress from './DigestProgress.vue'
import DigestRelease from './DigestRelease.vue'
import DigestStats from './DigestStats.vue'
import '@/assets/styles/portal/daily-digest-full.css'
import '@/assets/styles/portal/daily-digest-progress.css'

const props = defineProps({
  digest: { type: Object, required: true },
})
defineEmits(['close', 'leave', 'read-news', 'seen-news', 'open-release'])

const { formattedDate, greeting, statCards, level, achievement, expiry, forYou, events } =
  useDailyDigestPresenters(toRef(props, 'digest'))

// The ranking brings the first three, then the viewer when they are further down.
const podiumEntries = computed(() => props.digest.ranking?.top3 || [])
</script>
