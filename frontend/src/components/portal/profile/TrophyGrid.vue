<template>
  <div class="gc-trophy-box">
    <div class="gc-trophy-header">
      <h4 class="gc-box-title">{{ $t('portal.profile.trophies') }}</h4>
      <span class="gc-trophy-count">{{ unlockedCount }} <span>/ {{ displayTrophies.length }}</span></span>
    </div>

    <!-- Prochain success imminent -->
    <div v-if="nextAchievement" class="gc-trophy-next">
      <div class="gc-trophy-next-icon" :class="`gc-trophy-next-icon--${nextAchievement.tier_name}`">
        <component :is="iconMap[nextAchievement.icon] || HelpCircle" :size="24" />
      </div>
      <div class="gc-trophy-next-info">
        <div class="gc-trophy-next-name">
          {{ $t(nextAchievement.name_key) }}
          <span class="gc-trophy-tier" :class="`gc-trophy-tier--${nextAchievement.tier_name}`">{{ nextAchievement.tier_name }}</span>
        </div>
        <div class="gc-trophy-next-bar">
          <div class="gc-trophy-next-fill" :style="{ width: Math.round(100 * nextAchievement.progress / nextAchievement.threshold) + '%' }" />
        </div>
        <div class="gc-trophy-next-text">
          {{ nextAchievement.progress }}/{{ nextAchievement.threshold }} —
          <em>{{ $t('portal.profile.onlyLeft', { count: nextAchievement.threshold - nextAchievement.progress }) }}</em>
        </div>
      </div>
    </div>

    <!-- Trophy grid (paginated) -->
    <div ref="trophyGridRef" class="gc-trophy-grid">
      <div v-for="ach in visibleTrophies" :key="ach.id"
        class="gc-trophy"
        :class="[
          `gc-trophy--${ach.status}`,
          ach.status !== TROPHY_STATUS.SECRET && !ach.secret ? `gc-trophy--rarity-${ach.rarity}` : '',
          ach.status === TROPHY_STATUS.UNLOCKED ? `gc-fx gc-fx--${ach.tier_name}` : '',
          ach.secret && ach.status === TROPHY_STATUS.UNLOCKED ? `gc-trophy--secret-unlocked gc-secret-fx gc-secret-fx--${ach.secret_theme}` : ''
        ]"
        @click="$emit('select-trophy', ach)"
      >
        <span v-if="ach.status !== TROPHY_STATUS.SECRET || ach.status === TROPHY_STATUS.UNLOCKED" class="gc-trophy-tier-bar"
          :class="ach.secret && ach.secret_theme ? `gc-trophy-tier-bar--secret-${ach.secret_theme}` : `gc-trophy-tier-bar--${ach.tier_name}`" />

        <div v-if="ach.title_reward"
          class="gc-trophy-gift"
          :class="[
            `gc-trophy-gift--rarity-${ach.rarity}`,
            ach.status !== TROPHY_STATUS.UNLOCKED ? 'gc-trophy-gift--locked' : ''
          ]"
          :title="giftTooltip(ach)">
          <Gift :size="11" />
        </div>

        <TrophyFx :ach="ach" />

        <div class="gc-trophy-icon-wrap"
          :class="[
            (ach.status === TROPHY_STATUS.LOCKED || ach.status === TROPHY_STATUS.PROGRESS) ? 'gc-trophy-icon--dim' : '',
            ach.status === TROPHY_STATUS.UNLOCKED
              ? (ach.secret
                  ? `gc-icon-glow gc-icon-glow--${ach.secret_theme || ach.tier_name}`
                  : `gc-icon-glow gc-icon-glow--rarity-${ach.rarity}`)
              : ''
          ]">
          <HelpCircle v-if="ach.status === TROPHY_STATUS.SECRET" :size="24" />
          <component :is="iconMap[ach.icon] || HelpCircle" v-else :size="24" />
        </div>

        <div class="gc-trophy-label">{{ ach.status === TROPHY_STATUS.SECRET ? '???' : $t(ach.name_key) }}</div>

        <template v-if="ach.status === TROPHY_STATUS.UNLOCKED">
          <div class="gc-trophy-rarity" :class="`gc-trophy-rarity--${ach.rarity}`">{{ $t(`portal.profile.rarity.${ach.rarity}`) }}</div>
          <div class="gc-trophy-stars">{{ '⭐'.repeat(Math.min(6, ach.stars)) }}{{ '☆'.repeat(Math.max(0, 6 - ach.stars)) }}</div>
        </template>
        <template v-else-if="ach.status === TROPHY_STATUS.PROGRESS">
          <div class="gc-trophy-pbar"><div class="gc-trophy-pfill" :class="`gc-trophy-pfill--${ach.tier_name}`" :style="{ width: Math.round(100 * ach.progress / ach.threshold) + '%' }" /></div>
          <div class="gc-trophy-ptxt">{{ ach.progress }}/{{ ach.threshold }}</div>
        </template>
        <template v-else-if="ach.status === TROPHY_STATUS.SECRET">
          <div class="gc-trophy-rarity gc-trophy-rarity--epic">{{ $t('portal.profile.secretLabel') }}</div>
        </template>
        <template v-else>
          <div class="gc-trophy-ptxt">{{ ach.progress }}/{{ ach.threshold }}</div>
        </template>
      </div>
    </div>

    <div v-if="trophyTotalPages > 1" class="gc-trophy-pagination">
      <button class="gc-trophy-page-btn" :disabled="trophyPage === 0" @click="trophyPage = Math.max(0, trophyPage - 1)">←</button>
      <span class="gc-trophy-page-dots">
        <span v-for="p in trophyTotalPages" :key="p"
          class="gc-trophy-page-dot"
          :class="{ 'gc-trophy-page-dot--active': trophyPage === p - 1 }"
          @click="trophyPage = p - 1" />
      </span>
      <button class="gc-trophy-page-btn" :disabled="trophyPage >= trophyTotalPages - 1" @click="trophyPage = Math.min(trophyTotalPages - 1, trophyPage + 1)">→</button>
    </div>

    <button class="gc-trophy-see-all" @click="$emit('show-all')">
      {{ $t('portal.profile.seeAllTrophies', { count: displayTrophies.length }) }} →
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { HelpCircle, Gift } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import TrophyFx from './TrophyFx.vue'
import { TROPHY_STATUS, TROPHY_CATEGORY } from '@/constants/achievements'

const { t } = useI18n()

const props = defineProps({
  displayTrophies: { type: Array, required: true },
  unlockedCount: { type: Number, default: 0 },
  nextAchievement: { type: Object, default: null },
  iconMap: { type: Object, required: true },
  targetRows: { type: Number, default: 4 },
  mobileTargetRows: { type: Number, default: 2 },
})

defineEmits(['select-trophy', 'show-all'])

/**
 * Tooltip for the gift icon on trophy mini-cards. Mastery cards advertise
 * both the title reward and the unique avatar cosmetic (generic wording —
 * effect names are kept as surprises).
 */
function giftTooltip(ach) {
  const titleLabel = t('portal.profile.titleReward')
  const fxLabel = t('portal.profile.avatarEffectReward')
  if (ach.category === TROPHY_CATEGORY.MASTERY) {
    const titleName = ach.secret ? '' : ` : ${t(ach.title_reward)}`
    return `${titleLabel}${titleName} + ${fxLabel}`
  }
  return ach.secret ? titleLabel : `${titleLabel} : ${t(ach.title_reward)}`
}

const trophyGridRef = ref(null)
const trophyCols = ref(6)
const trophyPage = ref(0)
const isDesktop = ref(true)

// Sur mobile (< 768px) on réduit drastiquement le nombre de lignes pour limiter
// le nombre d'effets CSS animés rendus simultanément (sparkles, particules, halos)
// qui saturent le GPU des téléphones quand beaucoup de trophées sont débloqués.
const effectiveTargetRows = computed(() => isDesktop.value ? props.targetRows : props.mobileTargetRows)

const trophyPageSize = computed(() => (trophyCols.value || 6) * effectiveTargetRows.value)
const trophyTotalPages = computed(() => Math.max(1, Math.ceil(props.displayTrophies.length / trophyPageSize.value)))
const visibleTrophies = computed(() => {
  const start = trophyPage.value * trophyPageSize.value
  return props.displayTrophies.slice(start, start + trophyPageSize.value)
})

watch(trophyTotalPages, (total) => {
  if (trophyPage.value > total - 1) trophyPage.value = Math.max(0, total - 1)
})

function updateTrophyCols() {
  const grid = trophyGridRef.value
  if (!grid) return
  const style = getComputedStyle(grid)
  const cols = style.gridTemplateColumns.split(' ').length
  if (cols > 0) trophyCols.value = cols
}

let trophyResizeObserver = null
let desktopMql = null
function syncIsDesktop(e) { isDesktop.value = e.matches }

onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    desktopMql = window.matchMedia('(min-width: 768px)')
    isDesktop.value = desktopMql.matches
    desktopMql.addEventListener('change', syncIsDesktop)
  }
  if (typeof ResizeObserver !== 'undefined') {
    trophyResizeObserver = new ResizeObserver(() => updateTrophyCols())
  }
  const setupGrid = () => {
    if (trophyGridRef.value) {
      updateTrophyCols()
      trophyResizeObserver?.observe(trophyGridRef.value)
    } else {
      setTimeout(setupGrid, 100)
    }
  }
  setupGrid()
})
onBeforeUnmount(() => {
  trophyResizeObserver?.disconnect()
  desktopMql?.removeEventListener('change', syncIsDesktop)
})
</script>

<style>
@import '@/assets/styles/portal/trophy-grid.css';
</style>
