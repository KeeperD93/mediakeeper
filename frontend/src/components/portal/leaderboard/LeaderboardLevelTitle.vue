<template>
  {{
    $t('portal.leaderboard.hero.levelTitle', {
      level: entry.level,
      title: $t(`portal.profile.titles.${entry.title_key || 'spectator'}`),
    })
  }}
  <LeaderboardChosenTitle :entry="entry" />
</template>

<script setup>
import LeaderboardChosenTitle from '@/components/portal/leaderboard/LeaderboardChosenTitle.vue'

defineProps({
  entry: { type: Object, required: true },
})
</script>
