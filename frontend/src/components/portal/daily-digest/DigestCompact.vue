<template>
  <div class="ddc">
    <header class="ddc-head">
      <AvatarFrame
        class="ddc-head-av"
        :src="digest.me?.avatar_url || null"
        :name="digest.me?.display_name || ''"
        :size="40"
        :tier="digest.me?.tier || null"
        :effect="digest.me?.avatar_effect || null"
        aria-hidden="true"
      />
      <div class="dd-grow">
        <h1 class="ddc-hello">{{ greeting }}</h1>
        <span class="ddc-date">{{ formattedDate }}</span>
      </div>
    </header>

    <DigestExpiry v-if="expiry" :expiry="expiry" compact />

    <DigestCompactNews
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
      compact
      @open="$emit('open-release')"
    />

    <DigestStats v-if="statCards.length" :cards="statCards" compact />

    <DigestCompactProgress
      v-if="level"
      :level="level"
      :achievement="achievement"
      :entries="digest.ranking?.top3 || []"
      @leave="$emit('leave')"
    />

    <div v-if="digest.recent_adds?.length || forYou.length || events.length" class="ddc-split">
      <DigestPosters
        v-if="digest.recent_adds?.length"
        :items="digest.recent_adds"
        compact
        @leave="$emit('leave')"
      />
      <DigestUpNext
        v-if="forYou.length || events.length"
        :rows="forYou"
        :events="events"
        @leave="$emit('leave')"
      />
    </div>

    <footer class="ddc-foot">
      <p class="ddc-foot-text">{{ $t('portal.dailyDigest.footerShort') }}</p>
      <button type="button" class="dd-cta dd-cta--compact" @click="$emit('close')">
        {{ $t('common.close') }}
      </button>
    </footer>
  </div>
</template>

<script setup>
import { toRef } from 'vue'
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'
import { useDailyDigestPresenters } from '@/composables/portal/useDailyDigestPresenters'
import DigestCompactNews from './DigestCompactNews.vue'
import DigestCompactProgress from './DigestCompactProgress.vue'
import DigestExpiry from './DigestExpiry.vue'
import DigestPosters from './DigestPosters.vue'
import DigestRelease from './DigestRelease.vue'
import DigestStats from './DigestStats.vue'
import DigestUpNext from './DigestUpNext.vue'
import '@/assets/styles/portal/daily-digest-compact.css'

const props = defineProps({
  digest: { type: Object, required: true },
})
defineEmits(['close', 'leave', 'read-news', 'seen-news', 'open-release'])

const { formattedDate, greeting, statCards, level, achievement, expiry, forYou, events } =
  useDailyDigestPresenters(toRef(props, 'digest'))
</script>
