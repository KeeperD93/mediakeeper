<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ta-overlay">
      <div class="ta-panel">
        <!-- Header: global progress -->
        <div class="ta-header">
          <div class="ta-header-left">
            <h2 class="ta-title">{{ $t('portal.profile.trophies') }}</h2>
            <div class="ta-progress-wrap">
              <div class="ta-progress-bar">
                <div class="ta-progress-fill" :style="{ width: globalProgressPct + '%' }" />
              </div>
              <div class="ta-progress-text">
                <strong>{{ unlockedCount }}</strong>
                / {{ totalCount }}
                <span class="ta-progress-pct">({{ globalProgressPct }}%)</span>
              </div>
            </div>
          </div>
          <button class="ta-close" @click="$emit('update:modelValue', false)">&times;</button>
        </div>

        <div class="ta-body">
          <!-- Sidebar: categories -->
          <div class="ta-sidebar">
            <div class="ta-search">
              <Search class="ta-search-icon" :size="14" />
              <input
                v-model="searchQuery"
                type="text"
                class="ta-search-input"
                :placeholder="$t('common.search')"
              />
              <button v-if="searchQuery" class="ta-search-clear" @click="searchQuery = ''">
                ×
              </button>
            </div>
            <button
              class="ta-reward-chip"
              :class="{ 'ta-reward-chip--active': rewardFilterOnly }"
              :title="$t('portal.profile.rewardFilterHint')"
              @click="rewardFilterOnly = !rewardFilterOnly"
            >
              <Gift :size="12" />
              <span>{{ $t('portal.profile.rewardFilter') }}</span>
            </button>
            <div
              v-for="cat in categoriesWithStats"
              :key="cat.id"
              class="ta-cat"
              :class="{ 'ta-cat--active': selectedCategory === cat.id }"
              @click="$emit('update:selectedCategory', cat.id)"
            >
              <component :is="cat.icon" :size="18" class="ta-cat-icon" />
              <div class="ta-cat-info">
                <div class="ta-cat-name">{{ cat.label }}</div>
                <div class="ta-cat-count">{{ cat.unlocked }} / {{ cat.total }}</div>
              </div>
              <div class="ta-cat-bar">
                <div
                  class="ta-cat-bar-fill"
                  :style="{
                    width:
                      cat.total > 0 ? Math.round((100 * cat.unlocked) / cat.total) + '%' : '0%',
                  }"
                />
              </div>
            </div>
          </div>

          <!-- Main: trophy list for selected category -->
          <div class="ta-main">
            <div
              v-for="ach in searchedTrophies"
              :key="ach.id"
              class="ta-row"
              role="button"
              tabindex="0"
              :data-trophy-id="ach.id"
              :class="{
                'ta-row--unlocked': ach.status === TROPHY_STATUS.UNLOCKED,
                'ta-row--progress': ach.status === TROPHY_STATUS.PROGRESS,
                'ta-row--locked': ach.status === TROPHY_STATUS.LOCKED,
                'ta-row--secret': ach.status === TROPHY_STATUS.SECRET,
                'ta-row--focused': focusedId === ach.id,
                'ta-row--expanded': expandedId === ach.id,
                [`ta-row--rarity-${ach.rarity}`]: ach.status !== TROPHY_STATUS.SECRET,
              }"
              @click="toggleExpand(ach)"
              @keydown.enter.prevent="toggleExpand(ach)"
              @keydown.space.prevent="toggleExpand(ach)"
            >
              <div
                class="ta-row-icon"
                :class="[
                  ach.status === TROPHY_STATUS.LOCKED || ach.status === TROPHY_STATUS.PROGRESS
                    ? 'gc-trophy-icon--dim'
                    : '',
                ]"
              >
                <span
                  class="ta-row-icon-inner"
                  :class="
                    ach.status === TROPHY_STATUS.UNLOCKED
                      ? ach.secret
                        ? `gc-icon-glow gc-icon-glow--${ach.secret_theme || ach.tier_name}`
                        : `gc-icon-glow gc-icon-glow--rarity-${ach.rarity}`
                      : ''
                  "
                >
                  <HelpCircle v-if="ach.status === TROPHY_STATUS.SECRET" :size="28" />
                  <component :is="iconMap[ach.icon] || HelpCircle" v-else :size="28" />
                </span>
              </div>

              <div class="ta-row-info">
                <div class="ta-row-top">
                  <h4 class="ta-row-name">
                    {{ ach.status === TROPHY_STATUS.SECRET ? '???' : $t(ach.name_key) }}
                  </h4>
                  <span
                    v-if="ach.status === TROPHY_STATUS.UNLOCKED"
                    class="gc-trophy-rarity"
                    :class="`gc-trophy-rarity--${ach.rarity}`"
                  >
                    {{ $t(`portal.profile.rarity.${ach.rarity}`) }}
                  </span>
                </div>
                <div v-if="ach.status !== TROPHY_STATUS.SECRET" class="ta-row-desc">
                  {{ trophyDesc(ach) }}
                </div>
                <div v-else class="ta-row-desc">{{ $t('portal.profile.secretTrophy') }}</div>
                <div
                  v-if="ach.status !== TROPHY_STATUS.SECRET && ach.threshold"
                  class="ta-row-prog"
                >
                  <div class="ta-row-pbar">
                    <div
                      class="ta-row-pfill"
                      :class="`gc-trophy-pfill--${ach.tier_name}`"
                      :style="{
                        width:
                          Math.min(100, Math.round((100 * ach.progress) / ach.threshold)) + '%',
                      }"
                    />
                  </div>
                  <div class="ta-row-ptxt">
                    {{ Math.min(ach.progress, ach.threshold) }} / {{ ach.threshold }}
                  </div>
                </div>
              </div>

              <div class="ta-row-right">
                <!-- Title reward chip — always visible if the trophy grants a title.
                     Locked / secret state: greyed icon only, no reward name leaked.
                     Unlocked: current coloured design with name. -->
                <div
                  v-if="ach.title_reward"
                  class="ta-row-title-wrap"
                  :class="[
                    `ta-row-title-wrap--rarity-${ach.rarity}`,
                    ach.category === TROPHY_CATEGORY.MASTERY ? 'ta-row-title-wrap--master' : '',
                    ach.status !== TROPHY_STATUS.UNLOCKED ? 'ta-row-title-wrap--locked' : '',
                  ]"
                  :title="$t('portal.profile.titleReward')"
                >
                  <Crown
                    v-if="
                      ach.category === TROPHY_CATEGORY.MASTERY &&
                      ach.status === TROPHY_STATUS.UNLOCKED
                    "
                    :size="14"
                    class="ta-row-title-crown"
                  />
                  <Gift :size="13" class="ta-row-title-icon" />
                  <span v-if="ach.status === TROPHY_STATUS.UNLOCKED" class="ta-row-title">
                    <span class="ta-row-title-name">{{ $t(ach.title_reward) }}</span>
                  </span>
                </div>
                <!-- Unique avatar effect chip — shown for every mastery trophy,
                     greyed when locked. Secrets don't have mastery so no spoiler. -->
                <div
                  v-if="ach.category === TROPHY_CATEGORY.MASTERY"
                  class="ta-row-title-wrap ta-row-avatar-fx-wrap"
                  :class="{ 'ta-row-title-wrap--locked': ach.status !== TROPHY_STATUS.UNLOCKED }"
                  :title="$t('portal.profile.avatarEffectReward')"
                >
                  <Sparkles :size="13" class="ta-row-title-icon" />
                  <span v-if="ach.status === TROPHY_STATUS.UNLOCKED" class="ta-row-title">
                    <span class="ta-row-title-name">
                      {{ $t('portal.profile.avatarEffectReward') }}
                    </span>
                  </span>
                </div>
                <div v-if="ach.status === TROPHY_STATUS.UNLOCKED" class="ta-row-stars">
                  {{ '⭐'.repeat(Math.min(6, ach.stars))
                  }}{{ '☆'.repeat(Math.max(0, 6 - ach.stars)) }}
                </div>
                <div class="ta-row-xp">+{{ ach.xp_reward }} XP</div>
                <div
                  v-if="ach.status === TROPHY_STATUS.UNLOCKED && ach.unlocked_at"
                  class="ta-row-date"
                >
                  {{ new Date(ach.unlocked_at).toLocaleDateString() }}
                </div>
              </div>
              <button
                v-if="ach.status === TROPHY_STATUS.UNLOCKED"
                class="ta-row-pin"
                :class="{ 'ta-row-pin--active': pinnedIds.includes(ach.id) }"
                :disabled="!pinnedIds.includes(ach.id) && pinnedIds.length >= 5"
                :title="
                  pinnedIds.includes(ach.id)
                    ? $t('portal.profile.unpinBadge')
                    : $t('portal.profile.pinBadge')
                "
                @click.stop="$emit('toggle-pin', ach)"
              >
                <Pin :size="12" />
              </button>
              <span v-else class="ta-row-pin-spacer" aria-hidden="true"></span>
            </div>

            <div v-if="searchedTrophies.length === 0" class="ta-empty">
              {{ $t('portal.profile.noTrophiesInCategory') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { HelpCircle, Gift, Pin, Crown, Search, Sparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { TROPHY_STATUS, TROPHY_CATEGORY } from '@/constants/achievements'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  categoriesWithStats: { type: Array, required: true },
  filteredTrophies: { type: Array, required: true },
  selectedCategory: { type: String, default: 'all' },
  unlockedCount: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
  globalProgressPct: { type: Number, default: 0 },
  iconMap: { type: Object, required: true },
  focusTrophyId: { type: [String, Number], default: null },
  pinnedIds: { type: Array, default: () => [] },
})

defineEmits(['update:modelValue', 'update:selectedCategory', 'toggle-pin'])

const focusedId = ref(null)
const expandedId = ref(null)
function toggleExpand(ach) {
  expandedId.value = expandedId.value === ach.id ? null : ach.id
}

watch(
  () => [props.modelValue, props.focusTrophyId, props.selectedCategory],
  async ([open, fid]) => {
    if (!open || !fid) {
      focusedId.value = null
      return
    }
    await nextTick()
    const el = document.querySelector(`[data-trophy-id="${fid}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      focusedId.value = fid
      setTimeout(() => {
        if (focusedId.value === fid) focusedId.value = null
      }, 2200)
    }
  },
  { immediate: true },
)

const { t, te } = useI18n()
function trophyDesc(ach) {
  const key = ach.description_key
  if (!key) return ''
  return te(key) ? t(key) : ''
}

const searchQuery = ref('')
const rewardFilterOnly = ref(false)
const searchedTrophies = computed(() => {
  let list = props.filteredTrophies || []
  if (rewardFilterOnly.value) list = list.filter(ach => !!ach.title_reward)
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(ach => {
    const name = ach.name_key && te(ach.name_key) ? t(ach.name_key).toLowerCase() : ''
    const desc = trophyDesc(ach).toLowerCase()
    const titleReward =
      ach.title_reward && te(ach.title_reward) ? t(ach.title_reward).toLowerCase() : ''
    return name.includes(q) || desc.includes(q) || titleReward.includes(q)
  })
})
</script>

<style>
@import url('@/assets/styles/portal/trophy-overlay.css');
</style>
