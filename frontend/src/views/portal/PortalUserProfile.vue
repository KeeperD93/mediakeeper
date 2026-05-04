<template>
  <div :class="['pt-up', 'mk-page-root', `gc--${rankTier}`]">
    <div v-if="loading" class="pt-up-loading">
      <MkSpinner size="sm" inline />
      {{ $t('common.loading') }}
    </div>

    <div v-else-if="error === 'profile_private'" class="pt-up-empty">
      <Lock :size="32" />
      <h2>{{ $t('portal.settings.visibility.private') }}</h2>
      <p>{{ $t('portal.settings.visibility.privateHint') }}</p>
    </div>

    <div v-else-if="error === 'profile_not_found'" class="pt-up-empty">
      <UserX :size="32" />
      <h2>{{ $t('common.notFound') || '—' }}</h2>
    </div>

    <template v-else-if="data">
      <p v-if="data.admin_preview" class="pt-up-admin-banner">
        <Lock :size="14" />
        {{ $t('portal.settings.identity.adminPreviewBanner') }}
      </p>
      <header class="pt-up-hero">
        <!-- Mirror of /portal/me + /portal/settings: the RankSidebarCard
             is wrapped in `.gc.gc--{tier}` so it inherits the same
             tier-driven FX (border, glow, ring, particles…). -->
        <section class="gc" :class="`gc--${rankTier}`">
          <RankSidebarCard
            :profile-data="cardProfile"
            :rank-tier="rankTier"
            :title-key="titleKey"
            :title-tier-name="titleTierName"
            :ranking="rankingShape"
            :member-since="data.member_since_months"
            :xp-percent="xpPercent"
            :next-level-xp="nextLevelXp"
            :trophies="achievementsList"
            :icon-map="ICON_MAP"
            @edit-profile="goEdit"
          />
        </section>

        <div class="pt-up-summary">
          <h1 class="pt-up-name">{{ data.display_name }}</h1>
          <p v-if="data.bio" class="pt-up-bio">{{ data.bio }}</p>
          <p v-else class="pt-up-bio pt-up-bio--empty">—</p>

          <div class="pt-up-actions">
            <button
              v-if="data.is_self"
              type="button"
              class="pt-settings-btn pt-settings-btn--primary"
              @click="goEdit"
            >
              <Settings :size="14" />
              {{ $t('portal.profile.editProfile') }}
            </button>
            <button type="button" class="pt-settings-btn" @click="copyLink">
              <Link2 :size="14" />
              {{ copied ? $t('portal.settings.share.copied') : $t('portal.settings.share.copy') }}
            </button>
          </div>

          <dl class="pt-up-stats">
            <div class="pt-up-stat">
              <dt>{{ $t('portal.profile.level') }}</dt>
              <dd>{{ data.level }}</dd>
            </div>
            <div class="pt-up-stat">
              <dt>XP</dt>
              <dd>{{ (data.xp || 0).toLocaleString() }}</dd>
            </div>
            <div class="pt-up-stat">
              <dt>{{ $t('portal.profile.ranking') }}</dt>
              <dd>
                #{{ data.ranking?.position || '—' }}
                <small>· top {{ data.ranking?.percentile || '—' }}%</small>
              </dd>
            </div>
            <div class="pt-up-stat">
              <dt>{{ $t('portal.profile.trophies') }}</dt>
              <dd>{{ data.achievements?.unlocked || 0 }} / {{ data.achievements?.total || 0 }}</dd>
            </div>
          </dl>
        </div>
      </header>

      <section v-if="favoriteGenresLabels.length" class="pt-up-block">
        <h3 class="pt-up-block-title">{{ $t('portal.profile.yourGenres') }}</h3>
        <div class="pt-up-chips">
          <span v-for="g in favoriteGenresLabels" :key="g.label" class="pt-up-chip">
            <span>{{ g.emoji }}</span>
            <span>{{ $t(`portal.genres.${g.label}`) }}</span>
          </span>
        </div>
      </section>

      <section v-if="achievementsList.length" class="pt-up-block">
        <h3 class="pt-up-block-title">
          {{ $t('portal.profile.trophies') }}
          <span class="pt-up-block-count">{{ achievementsList.length }}</span>
        </h3>
        <div class="pt-up-trophy-grid">
          <div
            v-for="ach in achievementsList"
            :key="ach.id"
            class="pt-up-trophy"
            :class="`pt-up-trophy--${ach.rarity || ach.tier_name || 'common'}`"
            :title="$t(ach.name_key)"
          >
            <component :is="ICON_MAP[ach.icon] || HelpCircle" :size="22" />
            <span class="pt-up-trophy-name">{{ $t(ach.name_key) }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Link2, Lock, Settings, UserX, HelpCircle } from 'lucide-vue-next'

import MkSpinner from '@/components/common/MkSpinner.vue'
import RankSidebarCard from '@/components/portal/profile/RankSidebarCard.vue'
import { ICON_MAP } from '@/utils/portal/iconMap'
import { useApi } from '@/composables/useApi'
import { usePortalAchievements } from '@/composables/portal/usePortalAchievements'
import { xpForLevel } from '@/composables/portal/useProfileXp'

import '@/assets/styles/portal/settings-premium.css'
import '@/assets/styles/portal/user-profile.css'

const GENRE_LOOKUP = [
  { label: 'action', ids: [28, 10759], emoji: '💥' },
  { label: 'aventure', ids: [12], emoji: '⚔️' },
  { label: 'animation', ids: [16], emoji: '✏️' },
  { label: 'comedie', ids: [35], emoji: '😂' },
  { label: 'crime', ids: [80], emoji: '🔫' },
  { label: 'documentaire', ids: [99], emoji: '🎥' },
  { label: 'drame', ids: [18], emoji: '🎭' },
  { label: 'familial', ids: [10751], emoji: '👨‍👩‍👧' },
  { label: 'fantastique', ids: [14], emoji: '🧙' },
  { label: 'guerre', ids: [10752, 10768], emoji: '⚔️' },
  { label: 'histoire', ids: [36], emoji: '🏛️' },
  { label: 'horreur', ids: [27], emoji: '😱' },
  { label: 'mystere', ids: [9648], emoji: '🔍' },
  { label: 'musique', ids: [10402], emoji: '🎵' },
  { label: 'romance', ids: [10749], emoji: '❤️' },
  { label: 'scienceFiction', ids: [878, 10765], emoji: '🚀' },
  { label: 'thriller', ids: [53], emoji: '😰' },
  { label: 'western', ids: [37], emoji: '🤠' },
]

const route = useRoute()
const router = useRouter()
const { apiGet } = useApi()
const { fetchUserAchievements } = usePortalAchievements()

const loading = ref(true)
const error = ref(null)
const data = ref(null)
const achievementsList = ref([])
const copied = ref(false)

const userId = computed(() => Number(route.params.id))

const cardProfile = computed(() =>
  data.value ? { ...data.value, avatar_url: data.value.avatar_url } : null,
)

// Mirrors backend services/portal/profile_stats_ranking.py::tier_for_level
// so the rank tier (bronze → legendary) drives the same gradient/halo/ring
// treatment as on /portal/me and /portal/settings.
function tierForLevel(level) {
  if (level >= 50) return 'legendary'
  if (level >= 40) return 'master'
  if (level >= 30) return 'diamond'
  if (level >= 20) return 'platinum'
  if (level >= 11) return 'gold'
  if (level >= 6) return 'silver'
  return 'bronze'
}
function titleForLevel(level) {
  if (level >= 50) return 'legend'
  if (level >= 30) return 'master'
  if (level >= 20) return 'expert'
  if (level >= 12) return 'passionate'
  if (level >= 6) return 'regular'
  if (level >= 3) return 'amateur'
  return 'spectator'
}

const rankTier = computed(() => tierForLevel(data.value?.level || 1))
const titleKey = computed(() => titleForLevel(data.value?.level || 1))
const titleTierName = computed(() => rankTier.value)

const rankingShape = computed(() => ({
  position: data.value?.ranking?.position || 0,
  percentile: data.value?.ranking?.percentile || 50,
  movement: 0,
}))

const MAX_LEVEL = 50

const nextLevelXp = computed(() => {
  if (!data.value) return 100
  const level = Math.max(1, data.value.level || 1)
  if (level >= MAX_LEVEL) return xpForLevel(MAX_LEVEL)
  return xpForLevel(level + 1)
})
const xpPercent = computed(() => {
  if (!data.value) return 0
  const level = Math.max(1, data.value.level || 1)
  if (level >= MAX_LEVEL) return 100
  const floor = xpForLevel(level)
  const ceiling = xpForLevel(level + 1)
  const span = Math.max(1, ceiling - floor)
  const pos = (data.value.xp || 0) - floor
  return Math.max(0, Math.min(100, Math.round((pos / span) * 100)))
})

const favoriteGenresLabels = computed(() => {
  const ids = data.value?.favorite_genres || []
  if (!ids.length) return []
  return GENRE_LOOKUP.filter(g => g.ids.some(id => ids.includes(id)))
})

async function load() {
  loading.value = true
  error.value = null
  achievementsList.value = []
  data.value = null
  try {
    const res = await apiGet(`/api/portal/profiles/by-user-id/${userId.value}/public`)
    data.value = res
    if (res?.id) {
      achievementsList.value = await fetchUserAchievements(userId.value)
    }
  } catch (err) {
    error.value = err?.data?.detail || 'profile_not_found'
  } finally {
    loading.value = false
  }
}

function goEdit() {
  router.push({ name: 'portal-settings' })
}

async function copyLink() {
  try {
    const url = `${window.location.origin}/portal/u/${userId.value}`
    await navigator.clipboard.writeText(url)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    // Clipboard refused; fail silently — the user can copy from URL bar.
  }
}

watch(userId, load, { immediate: false })
onMounted(load)
</script>

<!-- Styles externalised to assets/styles/portal/user-profile.css; the
     extracted CSS keeps a unique class prefix to simulate Vue scoped CSS. -->
