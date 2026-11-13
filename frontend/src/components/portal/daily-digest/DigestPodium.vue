<template>
  <div class="dd-box dd-top3">
    <span class="dd-eyebrow dd-muted">{{ $t('portal.dailyDigest.sections.top3') }}</span>

    <div class="dd-podium">
      <component
        :is="row.to ? 'router-link' : 'div'"
        v-for="row in leaders"
        :key="row.place"
        :to="row.to"
        class="dd-pcard lb-metal"
        :class="[`lb-metal--${row.metal}`, `dd-pcard--${row.place}`]"
        @click="row.to ? $emit('leave') : null"
      >
        <span class="dd-prank lb-metal-digits">#{{ row.entry.rank }}</span>
        <AvatarFrame
          class="dd-pav"
          :src="row.entry.avatar_url || null"
          :name="row.entry.display_name || ''"
          :size="row.place === 1 ? 56 : 44"
          :tier="row.entry.tier || null"
          :effect="row.entry.avatar_effect || null"
          aria-hidden="true"
        />
        <span class="dd-pname">{{ row.entry.display_name }}</span>
        <span class="dd-pmeta">{{ row.levelShort }}</span>
        <span class="dd-pxp">{{ row.xp }}</span>
        <span class="dd-pfig">
          <span
            v-if="row.entry.trophies_won > 0"
            class="dd-trophies"
            role="img"
            :aria-label="row.trophies"
            :title="row.trophies"
          >
            +{{ row.entry.trophies_won }}
          </span>
          <span class="dd-mv" :class="`dd-mv--${row.move.tone}`" :title="row.moveTitle">
            {{ row.move.text }}
          </span>
        </span>
      </component>
    </div>

    <div v-if="me" class="dd-me">
      <span class="dd-me-pos">{{ me.entry.rank }}</span>
      <AvatarFrame
        class="dd-me-av"
        :src="me.entry.avatar_url || null"
        :name="me.entry.display_name || ''"
        :size="28"
        :tier="me.entry.tier || null"
        :effect="me.entry.avatar_effect || null"
        aria-hidden="true"
      />
      <span class="dd-me-info">
        <span class="dd-me-n">{{ me.entry.display_name }}</span>
        <span class="dd-me-pill">{{ $t('portal.leaderboard.myRank.label') }}</span>
        <span class="dd-me-tier">{{ me.levelLong }}</span>
      </span>
      <span class="dd-me-fig">
        <span class="dd-mv" :class="`dd-mv--${me.move.tone}`" :title="me.moveTitle">
          {{ me.move.text }}
        </span>
        <span class="dd-me-xp">{{ me.xp }}</span>
      </span>
    </div>

    <router-link
      :to="{ name: 'portal-leaderboard' }"
      class="dd-link dd-top3-link"
      @click="$emit('leave')"
    >
      {{ $t('portal.dailyDigest.top3.seeAll') }}
      <ChevronRight :size="16" aria-hidden="true" />
    </router-link>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight } from 'lucide-vue-next'
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'
import { rankingRows } from '@/utils/portal/dailyDigest'
import '@/assets/styles/portal/leaderboard-metal.css'
import '@/assets/styles/portal/daily-digest-podium.css'

const props = defineProps({
  // The first three of the month, then the viewer when they are further down.
  entries: { type: Array, required: true },
})
defineEmits(['leave'])

const { t } = useI18n()
const ranking = computed(() => rankingRows(props.entries, t))
const leaders = computed(() => ranking.value.leaders)
const me = computed(() => ranking.value.me)
</script>
