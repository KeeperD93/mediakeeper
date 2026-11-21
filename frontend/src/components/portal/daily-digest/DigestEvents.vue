<template>
  <section :aria-label="$t('portal.dailyDigest.sections.events')">
    <div class="dd-sh">
      <h2 class="dd-st">{{ $t('portal.dailyDigest.sections.events') }}</h2>
    </div>
    <div class="dd-events">
      <router-link
        v-for="ev in events"
        :key="ev.id"
        :to="ev.to"
        class="dd-ev"
        @click="$emit('leave')"
      >
        <span class="dd-ev-date">
          <b>{{ ev.day }}</b>
          <small>{{ ev.month }}</small>
        </span>
        <span class="dd-grow">
          <span class="dd-ev-k">{{ ev.kind }}</span>
          <span class="dd-ev-t">{{ ev.title }}</span>
          <span class="dd-ev-h">{{ ev.time }}</span>
        </span>
      </router-link>
    </div>
  </section>
</template>

<script setup>
import '@/assets/styles/portal/daily-digest-lists.css'

defineProps({
  // Upcoming events written by useDailyDigestPresenters (`events`): each opens its room.
  events: { type: Array, required: true },
})
defineEmits(['leave'])
</script>
