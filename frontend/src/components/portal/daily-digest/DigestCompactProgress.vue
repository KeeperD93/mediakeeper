<template>
  <section :aria-label="$t('portal.dailyDigest.sections.progress')">
    <div class="ddc-label">{{ $t('portal.dailyDigest.sections.progress') }}</div>
    <div class="ddc-box ddc-prog">
      <div class="ddc-prog-left">
        <div class="ddc-pi">
          <div
            class="ddc-ring"
            role="img"
            :aria-label="level.ringLabel"
            :style="{ '--dd-ring-pct': `${level.percent}%` }"
          >
            <span class="ddc-ring-in">{{ level.level }}</span>
          </div>
          <div class="dd-grow">
            <div class="ddc-pt">
              <span>{{ level.title }}</span>
              <small v-if="level.xpYesterday" class="ddc-pt-xp">{{ level.xpYesterday }}</small>
            </div>
            <div class="dd-bar ddc-bar">
              <span
                class="dd-bar-fill dd-bar-fill--level"
                :style="{ width: `${level.percent}%` }"
              />
            </div>
            <div class="ddc-sub">{{ level.toNextShort }}</div>
          </div>
        </div>
        <div v-if="achievement" class="ddc-pi">
          <div class="ddc-ic"><Trophy :size="20" aria-hidden="true" /></div>
          <div class="dd-grow">
            <div class="ddc-pt">
              <span>{{ achievement.name }}</span>
              <small class="ddc-pt-ach">{{ achievement.count }}</small>
            </div>
            <div class="dd-bar ddc-bar">
              <span
                class="dd-bar-fill dd-bar-fill--ach"
                :style="{ width: `${achievement.percent}%` }"
              />
            </div>
            <div class="ddc-sub">{{ achievement.remainingShort }}</div>
          </div>
        </div>
      </div>

      <div v-if="leaders.length" class="ddc-pi ddc-pi-top">
        <div class="dd-grow">
          <div class="ddc-pt">
            <span>{{ $t('portal.dailyDigest.sections.top3') }}</span>
            <router-link
              :to="{ name: 'portal-leaderboard' }"
              class="ddc-seeall"
              @click="$emit('leave')"
            >
              {{ $t('portal.dailyDigest.top3.seeAllShort') }}
            </router-link>
          </div>
          <div class="ddc-lb">
            <component
              :is="row.to ? 'router-link' : 'div'"
              v-for="row in leaders"
              :key="row.place"
              :to="row.to"
              class="ddc-lbrow"
              :class="`ddc-lbrow--${row.place}`"
              @click="row.to ? $emit('leave') : null"
            >
              <span class="ddc-lbpos">{{ row.entry.rank }}</span>
              <AvatarFrame
                class="ddc-lbav"
                :src="row.entry.avatar_url || null"
                :name="row.entry.display_name || ''"
                :size="22"
                :tier="row.entry.tier || null"
                :effect="row.entry.avatar_effect || null"
                aria-hidden="true"
              />
              <span class="ddc-lbn">{{ row.entry.display_name }}</span>
              <span v-if="row.move.n" class="ddc-mv" :class="`dd-mv--${row.move.tone}`">
                {{ row.move.text }}
              </span>
              <span
                v-else-if="row.entry.trophies_won > 0"
                class="ddc-lbtr"
                role="img"
                :aria-label="row.trophies"
                :title="row.trophies"
              >
                +{{ row.entry.trophies_won }}
              </span>
              <span class="ddc-lbxp">{{ row.xp }}</span>
            </component>
            <div v-if="me" class="ddc-lbrow ddc-lbrow--me">
              <span class="ddc-lbpos">{{ me.entry.rank }}</span>
              <AvatarFrame
                class="ddc-lbav"
                :src="me.entry.avatar_url || null"
                :name="me.entry.display_name || ''"
                :size="22"
                :tier="me.entry.tier || null"
                :effect="me.entry.avatar_effect || null"
                aria-hidden="true"
              />
              <span class="ddc-lbn">
                {{ me.entry.display_name }}
                <span class="ddc-lb-pill">{{ $t('portal.leaderboard.myRank.label') }}</span>
              </span>
              <span v-if="me.move.n" class="ddc-mv" :class="`dd-mv--${me.move.tone}`">
                {{ me.move.text }}
              </span>
              <span class="ddc-lbxp">{{ me.xp }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trophy } from 'lucide-vue-next'
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'
import { rankingRows } from '@/utils/portal/dailyDigest'
import '@/assets/styles/portal/daily-digest-compact-progress.css'

const props = defineProps({
  // Written by useDailyDigestPresenters (`level`, `achievement`).
  level: { type: Object, required: true },
  achievement: { type: Object, default: null },
  // The first three of the month, then the viewer when they are further down.
  entries: { type: Array, default: () => [] },
})
defineEmits(['leave'])

const { t } = useI18n()
// A row shows its move, or its trophies when it kept its place.
const ranking = computed(() => rankingRows(props.entries, t))
const leaders = computed(() => ranking.value.leaders)
const me = computed(() => ranking.value.me)
</script>
