<template>
  <div
    v-if="entries.length || widget || period"
    class="gc-lb-box"
    :class="{ 'gc-lb-box--widget': widget, 'gc-lb-box--tabs': period }"
  >
    <router-link
      v-if="!digest"
      :to="{ name: 'portal-leaderboard' }"
      class="gc-box-title gc-box-title--link"
      :class="{ 'gc-lb-widget-title': widget }"
      :title="$t('portal.profile.viewFullLeaderboard')"
    >
      {{ $t(period ? 'portal.profile.rankingShort' : 'portal.profile.ranking') }}
      <ChevronRight :size="14" :stroke-width="2.5" class="gc-box-title-chevron" />
    </router-link>
    <template v-if="period">
      <select
        v-model="period"
        class="gc-lb-select mk-select-chevron"
        :aria-label="$t('portal.leaderboard.periodsLabel')"
      >
        <option v-for="option in LEADERBOARD_PERIODS" :key="option" :value="option">
          {{ $t(`portal.leaderboard.periods.${option}`) }}
        </option>
      </select>
      <LeaderboardPeriodTabs v-model="period" :base-id="baseId" />
    </template>
    <div
      class="gc-lb-rows"
      :data-full="entries.length > LEADERBOARD_PROFILE_LIMIT || null"
      v-bind="panelAttrs"
    >
      <p v-if="stateKey" class="gc-lb-state">{{ $t(stateKey) }}</p>
      <template v-else>
        <component
          :is="entry.user_id ? 'router-link' : 'div'"
          v-for="entry in entries"
          :key="entry.rank"
          :to="
            entry.user_id
              ? { name: 'portal-user-profile', params: { id: entry.user_id } }
              : undefined
          "
          class="gc-lb-row"
          :class="{
            ['gc-lb-row--' + entry.rank]: entry.rank <= 3,
            'gc-lb-row--me': entry.is_current_user,
            'gc-lb-row--linkable': !!entry.user_id,
          }"
        >
          <span class="gc-lb-pos">{{ entry.rank }}</span>
          <div class="gc-lb-av">
            <MkAvatar
              :name="entry.display_name || ''"
              :src="entry.avatar_url || null"
              :size="28"
              :tier="entry.tier || 'bronze'"
            />
          </div>
          <div class="gc-lb-info">
            <span class="gc-lb-n">{{ entry.display_name }}</span>
            <LeaderboardMePill v-if="entry.is_current_user" />
            <span class="gc-lb-tier">
              <LeaderboardLevelTitle :entry="entry" />
            </span>
          </div>
          <span class="gc-lb-figures">
            <LeaderboardTrophies :count="entry.trophies_won" />
            <LeaderboardMove :movement="entry.movement" :period="period || undefined" />
            <span class="gc-lb-v">{{ (entry.period_xp || 0).toLocaleString() }} XP</span>
          </span>
        </component>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import LeaderboardLevelTitle from '@/components/portal/leaderboard/LeaderboardLevelTitle.vue'
import LeaderboardMePill from '@/components/portal/leaderboard/LeaderboardMePill.vue'
import LeaderboardMove from '@/components/portal/leaderboard/LeaderboardMove.vue'
import LeaderboardPeriodTabs from '@/components/portal/leaderboard/LeaderboardPeriodTabs.vue'
import LeaderboardTrophies from '@/components/portal/leaderboard/LeaderboardTrophies.vue'
import { LEADERBOARD_PERIODS, LEADERBOARD_PROFILE_LIMIT } from '@/constants/leaderboard'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  widget: { type: Boolean, default: false },
  // The daily digest: its section already names the card, which shows no title.
  digest: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

// Null on the admin widget and the daily digest: the month, with no choice of period.
const period = defineModel('period', { type: String, default: null })

const baseId = useId()

const panelAttrs = computed(() =>
  period.value
    ? {
        id: `${baseId}-panel`,
        role: 'tabpanel',
        'aria-labelledby': `${baseId}-tab-${period.value}`,
      }
    : {},
)

const stateKey = computed(() => {
  if (!period.value) return null
  if (props.loading) return 'common.loading'
  return props.entries.length ? null : `portal.leaderboard.emptyState.${period.value}`
})
</script>

<style>
@import url('@/assets/styles/portal/leaderboard-card.css');
</style>

<style scoped>
/* The rows of the leaderboard page, wherever the card is shown: they follow its width. */
.gc-lb-box {
  container: lb-card / inline-size;
}

/* With a choice of period: the title shares its row with the menu, the rest takes
   the full width. The rows stay at the top of a card its neighbours stretch. */
.gc-lb-box--tabs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  align-content: start;
  gap: var(--portal-space-2);
}
.gc-lb-box--tabs .gc-box-title {
  position: relative;
  justify-self: start;
  margin-bottom: 0;
}
/* The tabs come later in the page: where this band reaches them, they win the touch. */
.gc-lb-box--tabs .gc-box-title::after {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: var(--portal-touch-target);
  transform: translateY(-50%);
}
.gc-lb-box--tabs .gc-lb-rows {
  grid-column: 1 / -1;
}

.gc-lb-select {
  /* As wide as the word shown, not as the longest one of the list. */
  field-sizing: content;
  min-height: var(--portal-touch-target);
  padding-block: var(--portal-space-1);
  padding-left: var(--portal-space-3);
  font-family: inherit;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-medium);
  color: var(--portal-text-primary);
  background-color: var(--portal-surface-3);
  border: var(--portal-border-width) solid var(--portal-border-default);
  /* main.css forces the radius of every native select. */
  border-radius: var(--portal-radius-lg) !important;
  cursor: pointer;
}
.gc-lb-select:focus-visible {
  outline: var(--portal-focus-ring);
  outline-offset: var(--portal-focus-ring-offset);
}
.gc-lb-select option {
  color: var(--portal-text-primary);
  background-color: var(--portal-bg-primary);
}
/* iOS zooms the page into a field under 16px it focuses: 16px there only. */
@supports (-webkit-touch-callout: none) {
  .gc-lb-select {
    font-size: var(--portal-text-md);
  }
}

/* Their margins follow the card here: the screen says nothing of its width. */
.gc-lb-box--tabs .lb-period-tabs {
  display: none;
  grid-column: 1 / -1;
  gap: var(--portal-space-3-5) clamp(var(--portal-space-1), 1.5cqi, var(--portal-space-2));
}
.gc-lb-box--tabs :deep(.lb-period-tab) {
  padding-inline: clamp(
    var(--portal-space-1-5),
    5cqi - var(--portal-space-2),
    var(--portal-space-3-5)
  );
}

/* The XP with its arrow, the trophies under them: under the name in a narrow card,
   beside it in a wider one, every row alike so that they line up. */
.gc-lb-box .gc-lb-row {
  column-gap: var(--portal-space-2);
  padding-inline: var(--portal-space-1-5);
}
.gc-lb-box .gc-lb-figures {
  flex-basis: 100%;
  display: grid;
  grid-template-columns: auto auto;
  justify-content: end;
  place-items: center end;
  gap: var(--portal-space-1);
}
.gc-lb-box .gc-lb-move {
  grid-area: 1 / 1;
  min-width: 0;
  line-height: var(--portal-lh-tight);
}
/* Always the last column: without an arrow, the first one stays empty. Without the
   space its line keeps above the digits, the block sits centered in the row. */
.gc-lb-box .gc-lb-v {
  grid-area: 1 / 2;
  line-height: var(--portal-lh-tight);
  text-box: trim-both cap alphabetic;
}
.gc-lb-box .lb-trophies {
  grid-row: 2;
  grid-column: 1 / -1;
}

/* The viewer's row, as on the leaderboard page: the label goes under a name that
   needs the room, and only the name can be cut. */
.gc-lb-box .gc-lb-row--me {
  border-left: var(--portal-border-width-accent) solid var(--portal-accent-500);
  background: var(--portal-row-me-bg);
}
.gc-lb-box .gc-lb-info {
  flex-flow: row wrap;
  align-items: center;
  column-gap: var(--portal-space-1-5);
}
.gc-lb-box .gc-lb-n {
  flex: 0 1 auto;
}
.gc-lb-box .gc-lb-tier {
  flex: 0 0 100%;
}

.gc-lb-state {
  margin: 0;
  padding-block: var(--portal-space-6);
  font-size: var(--portal-text-xs);
  color: var(--portal-text-muted-solid);
  text-align: center;
}

@media (min-width: 768px) {
  .gc-lb-box--tabs .gc-box-title::after {
    content: none;
  }
  /* A laptop's narrowest card leaves the menu just this much next to the title. */
  .gc-lb-select {
    min-height: 0;
    font-size: var(--portal-text-2xs);
  }
}

/* A query cannot read a token: its width stays a number, like the breakpoints of a
   media query. Here, where a name keeps about 100 px next to the largest figures. */
@container lb-card (min-width: 270px) {
  .gc-lb-box .gc-lb-row {
    flex-wrap: nowrap;
  }
  .gc-lb-box .gc-lb-figures {
    flex: none;
  }
}

/* The menu up to a 375 px screen, the four tabs on one line beyond. */
@container lb-card (min-width: 284px) {
  .gc-lb-select {
    display: none;
  }
  .gc-lb-box--tabs .lb-period-tabs {
    display: flex;
  }
}
</style>
